/*
 * Unified Tempera auth: PKCE (S256) helpers, audience-aware OAuth request
 * builders, and a credential store that yields the right bearer per audience.
 *
 * The library is dependency-free and HTTP-less, so SHA-256 is implemented here
 * rather than linked, token endpoint bodies are returned as
 * application/x-www-form-urlencoded strings for the caller's HTTP client, and
 * refresh-token rotation is applied through
 * tempera_auth_apply_token_response().
 */

#include <stdlib.h>
#include <string.h>

#include "internal.h"

typedef struct token_set {
    char *audience;
    char *access_token;
    char *refresh_token;
    long long expires_in;
    char *scope;
} token_set;

struct tempera_auth {
    char *issuer_url;
    char *client_id;
    char *api_key;
    token_set *tokens;
    size_t token_count;
};

/* ------------------------------------------------------------------------ */
/* SHA-256                                                                   */
/* ------------------------------------------------------------------------ */

static const unsigned long SHA256_K[64] = {
    0x428a2f98UL, 0x71374491UL, 0xb5c0fbcfUL, 0xe9b5dba5UL, 0x3956c25bUL, 0x59f111f1UL,
    0x923f82a4UL, 0xab1c5ed5UL, 0xd807aa98UL, 0x12835b01UL, 0x243185beUL, 0x550c7dc3UL,
    0x72be5d74UL, 0x80deb1feUL, 0x9bdc06a7UL, 0xc19bf174UL, 0xe49b69c1UL, 0xefbe4786UL,
    0x0fc19dc6UL, 0x240ca1ccUL, 0x2de92c6fUL, 0x4a7484aaUL, 0x5cb0a9dcUL, 0x76f988daUL,
    0x983e5152UL, 0xa831c66dUL, 0xb00327c8UL, 0xbf597fc7UL, 0xc6e00bf3UL, 0xd5a79147UL,
    0x06ca6351UL, 0x14292967UL, 0x27b70a85UL, 0x2e1b2138UL, 0x4d2c6dfcUL, 0x53380d13UL,
    0x650a7354UL, 0x766a0abbUL, 0x81c2c92eUL, 0x92722c85UL, 0xa2bfe8a1UL, 0xa81a664bUL,
    0xc24b8b70UL, 0xc76c51a3UL, 0xd192e819UL, 0xd6990624UL, 0xf40e3585UL, 0x106aa070UL,
    0x19a4c116UL, 0x1e376c08UL, 0x2748774cUL, 0x34b0bcb5UL, 0x391c0cb3UL, 0x4ed8aa4aUL,
    0x5b9cca4fUL, 0x682e6ff3UL, 0x748f82eeUL, 0x78a5636fUL, 0x84c87814UL, 0x8cc70208UL,
    0x90befffaUL, 0xa4506cebUL, 0xbef9a3f7UL, 0xc67178f2UL};

#define MASK32 0xffffffffUL

static unsigned long rotate_right(unsigned long value, unsigned int bits)
{
    value &= MASK32;
    return ((value >> bits) | (value << (32 - bits))) & MASK32;
}

static void sha256_block(unsigned long *hash, const unsigned char *chunk)
{
    unsigned long w[64];
    unsigned long a, b, c, d, e, f, g, h;
    unsigned int index;

    for (index = 0; index < 16; index++) {
        w[index] = ((unsigned long)chunk[4 * index] << 24) |
                   ((unsigned long)chunk[4 * index + 1] << 16) |
                   ((unsigned long)chunk[4 * index + 2] << 8) |
                   (unsigned long)chunk[4 * index + 3];
    }
    for (index = 16; index < 64; index++) {
        unsigned long s0 = rotate_right(w[index - 15], 7) ^ rotate_right(w[index - 15], 18) ^
                           ((w[index - 15] & MASK32) >> 3);
        unsigned long s1 = rotate_right(w[index - 2], 17) ^ rotate_right(w[index - 2], 19) ^
                           ((w[index - 2] & MASK32) >> 10);

        w[index] = (w[index - 16] + s0 + w[index - 7] + s1) & MASK32;
    }
    a = hash[0];
    b = hash[1];
    c = hash[2];
    d = hash[3];
    e = hash[4];
    f = hash[5];
    g = hash[6];
    h = hash[7];
    for (index = 0; index < 64; index++) {
        unsigned long s1 = rotate_right(e, 6) ^ rotate_right(e, 11) ^ rotate_right(e, 25);
        unsigned long ch = (e & f) ^ ((~e & MASK32) & g);
        unsigned long temp1 = (h + s1 + ch + SHA256_K[index] + w[index]) & MASK32;
        unsigned long s0 = rotate_right(a, 2) ^ rotate_right(a, 13) ^ rotate_right(a, 22);
        unsigned long maj = (a & b) ^ (a & c) ^ (b & c);
        unsigned long temp2 = (s0 + maj) & MASK32;

        h = g;
        g = f;
        f = e;
        e = (d + temp1) & MASK32;
        d = c;
        c = b;
        b = a;
        a = (temp1 + temp2) & MASK32;
    }
    hash[0] = (hash[0] + a) & MASK32;
    hash[1] = (hash[1] + b) & MASK32;
    hash[2] = (hash[2] + c) & MASK32;
    hash[3] = (hash[3] + d) & MASK32;
    hash[4] = (hash[4] + e) & MASK32;
    hash[5] = (hash[5] + f) & MASK32;
    hash[6] = (hash[6] + g) & MASK32;
    hash[7] = (hash[7] + h) & MASK32;
}

static void sha256(const unsigned char *data, size_t length, unsigned char out[32])
{
    unsigned long hash[8] = {0x6a09e667UL, 0xbb67ae85UL, 0x3c6ef372UL, 0xa54ff53aUL,
                             0x510e527fUL, 0x9b05688cUL, 0x1f83d9abUL, 0x5be0cd19UL};
    unsigned char tail[128];
    size_t tail_length;
    size_t offset;
    unsigned long long bit_length = (unsigned long long)length * 8ULL;
    unsigned int index;

    for (offset = 0; offset + 64 <= length; offset += 64) {
        sha256_block(hash, data + offset);
    }
    tail_length = length - offset;
    memcpy(tail, data + offset, tail_length);
    tail[tail_length++] = 0x80;
    while (tail_length % 64 != 56) {
        tail[tail_length++] = 0;
    }
    for (index = 0; index < 8; index++) {
        tail[tail_length++] = (unsigned char)((bit_length >> (56 - 8 * index)) & 0xffULL);
    }
    for (offset = 0; offset < tail_length; offset += 64) {
        sha256_block(hash, tail + offset);
    }
    for (index = 0; index < 8; index++) {
        out[4 * index] = (unsigned char)((hash[index] >> 24) & 0xffUL);
        out[4 * index + 1] = (unsigned char)((hash[index] >> 16) & 0xffUL);
        out[4 * index + 2] = (unsigned char)((hash[index] >> 8) & 0xffUL);
        out[4 * index + 3] = (unsigned char)(hash[index] & 0xffUL);
    }
}

/* ------------------------------------------------------------------------ */
/* base64url and PKCE                                                        */
/* ------------------------------------------------------------------------ */

static const char BASE64URL_ALPHABET[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

char *tempera_base64url_no_pad(const unsigned char *data, size_t length)
{
    tempera_buf buf;
    size_t offset;

    if (data == NULL && length > 0) {
        return NULL;
    }
    tempera_buf_init(&buf);
    for (offset = 0; offset < length; offset += 3) {
        size_t remaining = length - offset;
        unsigned long b0 = data[offset];
        unsigned long b1 = remaining > 1 ? data[offset + 1] : 0UL;
        unsigned long b2 = remaining > 2 ? data[offset + 2] : 0UL;
        unsigned long triple = (b0 << 16) | (b1 << 8) | b2;

        tempera_buf_append_char(&buf, BASE64URL_ALPHABET[(triple >> 18) & 0x3fUL]);
        tempera_buf_append_char(&buf, BASE64URL_ALPHABET[(triple >> 12) & 0x3fUL]);
        if (remaining > 1) {
            tempera_buf_append_char(&buf, BASE64URL_ALPHABET[(triple >> 6) & 0x3fUL]);
        }
        if (remaining > 2) {
            tempera_buf_append_char(&buf, BASE64URL_ALPHABET[triple & 0x3fUL]);
        }
    }
    return tempera_buf_finish(&buf);
}

char *tempera_pkce_challenge_s256(const char *verifier)
{
    unsigned char digest[32];

    if (verifier == NULL) {
        return NULL;
    }
    sha256((const unsigned char *)verifier, strlen(verifier), digest);
    return tempera_base64url_no_pad(digest, sizeof(digest));
}

char *tempera_pkce_verifier_from_entropy(const unsigned char *entropy, size_t length)
{
    return tempera_base64url_no_pad(entropy, length);
}

tempera_pkce_pair tempera_pkce_pair_from_entropy(const unsigned char *entropy, size_t length)
{
    tempera_pkce_pair pair;

    pair.verifier = tempera_pkce_verifier_from_entropy(entropy, length);
    pair.challenge = pair.verifier != NULL ? tempera_pkce_challenge_s256(pair.verifier) : NULL;
    pair.method = "S256";
    if (pair.challenge == NULL) {
        tempera_string_free(pair.verifier);
        pair.verifier = NULL;
    }
    return pair;
}

void tempera_pkce_pair_free(tempera_pkce_pair *pair)
{
    if (pair == NULL) {
        return;
    }
    tempera_string_free(pair->verifier);
    tempera_string_free(pair->challenge);
    pair->verifier = NULL;
    pair->challenge = NULL;
}

/* ------------------------------------------------------------------------ */
/* Form encoding                                                             */
/* ------------------------------------------------------------------------ */

typedef struct form_pair {
    const char *key;
    const char *value;
} form_pair;

static char *form_encode(const form_pair *pairs, size_t count)
{
    tempera_buf buf;
    size_t index;

    tempera_buf_init(&buf);
    for (index = 0; index < count; index++) {
        char *key = tempera_url_encode(pairs[index].key);
        char *value = tempera_url_encode(pairs[index].value);

        if (key == NULL || value == NULL) {
            tempera_string_free(key);
            tempera_string_free(value);
            tempera_buf_dispose(&buf);
            return NULL;
        }
        if (index > 0) {
            tempera_buf_append_char(&buf, '&');
        }
        tempera_buf_append(&buf, key);
        tempera_buf_append_char(&buf, '=');
        tempera_buf_append(&buf, value);
        tempera_string_free(key);
        tempera_string_free(value);
    }
    return tempera_buf_finish(&buf);
}

/* ------------------------------------------------------------------------ */
/* Credential store                                                          */
/* ------------------------------------------------------------------------ */

static void token_set_dispose(token_set *tokens)
{
    free(tokens->audience);
    free(tokens->access_token);
    free(tokens->refresh_token);
    free(tokens->scope);
    memset(tokens, 0, sizeof(*tokens));
}

static token_set *find_tokens(const tempera_auth *auth, const char *audience)
{
    size_t index;

    if (auth == NULL || audience == NULL) {
        return NULL;
    }
    for (index = 0; index < auth->token_count; index++) {
        if (strcmp(auth->tokens[index].audience, audience) == 0) {
            return &auth->tokens[index];
        }
    }
    return NULL;
}

tempera_auth *tempera_auth_new(const char *issuer_url)
{
    tempera_auth *auth;
    size_t length;

    if (issuer_url == NULL) {
        return NULL;
    }
    auth = (tempera_auth *)calloc(1, sizeof(*auth));
    if (auth == NULL) {
        return NULL;
    }
    length = strlen(issuer_url);
    while (length > 0 && issuer_url[length - 1] == '/') {
        length--;
    }
    auth->issuer_url = tempera_strndup(issuer_url, length);
    if (auth->issuer_url == NULL) {
        free(auth);
        return NULL;
    }
    return auth;
}

void tempera_auth_free(tempera_auth *auth)
{
    size_t index;

    if (auth == NULL) {
        return;
    }
    for (index = 0; index < auth->token_count; index++) {
        token_set_dispose(&auth->tokens[index]);
    }
    free(auth->tokens);
    free(auth->issuer_url);
    free(auth->client_id);
    free(auth->api_key);
    free(auth);
}

static tempera_status replace_string(char **slot, const char *value)
{
    char *copy = NULL;

    if (value != NULL) {
        copy = tempera_strdup(value);
        if (copy == NULL) {
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
    }
    free(*slot);
    *slot = copy;
    return TEMPERA_OK;
}

tempera_status tempera_auth_set_client_id(tempera_auth *auth, const char *client_id)
{
    if (auth == NULL) {
        return TEMPERA_ERR_INVALID_ARGUMENT;
    }
    return replace_string(&auth->client_id, client_id);
}

tempera_status tempera_auth_set_api_key(tempera_auth *auth, const char *api_key)
{
    if (auth == NULL) {
        return TEMPERA_ERR_INVALID_ARGUMENT;
    }
    return replace_string(&auth->api_key, api_key);
}

tempera_status tempera_auth_apply_token_response(tempera_auth *auth,
                                                 const char *audience,
                                                 const char *access_token,
                                                 const char *refresh_token,
                                                 long long expires_in,
                                                 const char *scope)
{
    token_set *slot;
    char *access_copy;
    char *refresh_copy = NULL;
    char *scope_copy = NULL;

    if (auth == NULL || audience == NULL || access_token == NULL) {
        return TEMPERA_ERR_INVALID_ARGUMENT;
    }
    access_copy = tempera_strdup(access_token);
    if (access_copy == NULL) {
        return TEMPERA_ERR_OUT_OF_MEMORY;
    }
    if (refresh_token != NULL) {
        refresh_copy = tempera_strdup(refresh_token);
        if (refresh_copy == NULL) {
            free(access_copy);
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
    }
    if (scope != NULL) {
        scope_copy = tempera_strdup(scope);
        if (scope_copy == NULL) {
            free(access_copy);
            free(refresh_copy);
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
    }

    slot = find_tokens(auth, audience);
    if (slot == NULL) {
        token_set *grown =
            (token_set *)realloc(auth->tokens, (auth->token_count + 1) * sizeof(*grown));

        if (grown == NULL) {
            free(access_copy);
            free(refresh_copy);
            free(scope_copy);
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
        auth->tokens = grown;
        slot = &auth->tokens[auth->token_count];
        memset(slot, 0, sizeof(*slot));
        slot->audience = tempera_strdup(audience);
        if (slot->audience == NULL) {
            free(access_copy);
            free(refresh_copy);
            free(scope_copy);
            return TEMPERA_ERR_OUT_OF_MEMORY;
        }
        auth->token_count++;
    }

    free(slot->access_token);
    slot->access_token = access_copy;
    if (refresh_copy != NULL) {
        /* Rotation: a newly issued refresh token replaces the old one. */
        free(slot->refresh_token);
        slot->refresh_token = refresh_copy;
    }
    free(slot->scope);
    slot->scope = scope_copy;
    slot->expires_in = expires_in;
    return TEMPERA_OK;
}

const char *tempera_auth_bearer_for(const tempera_auth *auth, const char *audience)
{
    const token_set *tokens;

    if (auth == NULL) {
        return NULL;
    }
    tokens = find_tokens(auth, audience);
    if (tokens != NULL && tokens->access_token != NULL) {
        return tokens->access_token;
    }
    return auth->api_key;
}

char *tempera_auth_authorization_header(const tempera_auth *auth, const char *audience)
{
    const char *bearer = tempera_auth_bearer_for(auth, audience);
    tempera_buf buf;

    if (bearer == NULL) {
        return NULL;
    }
    tempera_buf_init(&buf);
    tempera_buf_append(&buf, "Bearer ");
    tempera_buf_append(&buf, bearer);
    return tempera_buf_finish(&buf);
}

const char *tempera_auth_issuer_url(const tempera_auth *auth)
{
    return auth == NULL ? NULL : auth->issuer_url;
}

static char *issuer_join(const tempera_auth *auth, const char *path)
{
    tempera_buf buf;

    if (auth == NULL) {
        return NULL;
    }
    tempera_buf_init(&buf);
    tempera_buf_append(&buf, auth->issuer_url);
    tempera_buf_append(&buf, path);
    return tempera_buf_finish(&buf);
}

char *tempera_auth_token_url(const tempera_auth *auth)
{
    return issuer_join(auth, TEMPERA_TOKEN_PATH);
}

char *tempera_auth_revoke_url(const tempera_auth *auth)
{
    return issuer_join(auth, TEMPERA_REVOKE_PATH);
}

char *tempera_auth_mcp_url(const tempera_auth *auth)
{
    return issuer_join(auth, TEMPERA_MCP_PATH);
}

char *tempera_auth_authorize_url(const tempera_auth *auth,
                                 const tempera_authorize_url_params *params)
{
    form_pair pairs[8];
    size_t count = 0;
    char *query;
    tempera_buf buf;

    if (auth == NULL || params == NULL || params->client_id == NULL ||
        params->redirect_uri == NULL || params->code_challenge == NULL ||
        params->audience == NULL) {
        return NULL;
    }
    pairs[count].key = "response_type";
    pairs[count++].value = "code";
    pairs[count].key = "client_id";
    pairs[count++].value = params->client_id;
    pairs[count].key = "redirect_uri";
    pairs[count++].value = params->redirect_uri;
    pairs[count].key = "code_challenge";
    pairs[count++].value = params->code_challenge;
    pairs[count].key = "code_challenge_method";
    pairs[count++].value = "S256";
    pairs[count].key = "resource";
    pairs[count++].value = params->audience;
    if (params->scope != NULL) {
        pairs[count].key = "scope";
        pairs[count++].value = params->scope;
    }
    if (params->state != NULL) {
        pairs[count].key = "state";
        pairs[count++].value = params->state;
    }
    query = form_encode(pairs, count);
    if (query == NULL) {
        return NULL;
    }
    tempera_buf_init(&buf);
    tempera_buf_append(&buf, auth->issuer_url);
    tempera_buf_append(&buf, TEMPERA_AUTHORIZE_PATH);
    tempera_buf_append_char(&buf, '?');
    tempera_buf_append(&buf, query);
    tempera_string_free(query);
    return tempera_buf_finish(&buf);
}

char *tempera_auth_code_exchange_body(const tempera_auth *auth,
                                      const char *code,
                                      const char *code_verifier,
                                      const char *redirect_uri,
                                      const char *audience)
{
    form_pair pairs[6];
    size_t count = 0;

    if (auth == NULL || code == NULL || code_verifier == NULL || redirect_uri == NULL ||
        audience == NULL) {
        return NULL;
    }
    pairs[count].key = "grant_type";
    pairs[count++].value = "authorization_code";
    pairs[count].key = "code";
    pairs[count++].value = code;
    pairs[count].key = "code_verifier";
    pairs[count++].value = code_verifier;
    pairs[count].key = "redirect_uri";
    pairs[count++].value = redirect_uri;
    pairs[count].key = "resource";
    pairs[count++].value = audience;
    if (auth->client_id != NULL) {
        pairs[count].key = "client_id";
        pairs[count++].value = auth->client_id;
    }
    return form_encode(pairs, count);
}

char *tempera_auth_refresh_body(const tempera_auth *auth, const char *audience)
{
    const token_set *tokens = find_tokens(auth, audience);
    form_pair pairs[4];
    size_t count = 0;

    if (tokens == NULL || tokens->refresh_token == NULL) {
        return NULL;
    }
    pairs[count].key = "grant_type";
    pairs[count++].value = "refresh_token";
    pairs[count].key = "refresh_token";
    pairs[count++].value = tokens->refresh_token;
    pairs[count].key = "resource";
    pairs[count++].value = audience;
    if (auth->client_id != NULL) {
        pairs[count].key = "client_id";
        pairs[count++].value = auth->client_id;
    }
    return form_encode(pairs, count);
}

char *tempera_auth_revoke_body(tempera_auth *auth, const char *audience)
{
    token_set *tokens = find_tokens(auth, audience);
    form_pair pairs[3];
    size_t count = 0;
    char *body;
    size_t index;

    if (tokens == NULL) {
        return NULL;
    }
    pairs[count].key = "token";
    pairs[count++].value =
        tokens->refresh_token != NULL ? tokens->refresh_token : tokens->access_token;
    pairs[count].key = "token_type_hint";
    pairs[count++].value = "refresh_token";
    if (auth->client_id != NULL) {
        pairs[count].key = "client_id";
        pairs[count++].value = auth->client_id;
    }
    body = form_encode(pairs, count);

    /* Revoking drops the stored token set, exactly as the Rust builder does. */
    index = (size_t)(tokens - auth->tokens);
    token_set_dispose(tokens);
    memmove(&auth->tokens[index], &auth->tokens[index + 1],
            (auth->token_count - index - 1) * sizeof(*auth->tokens));
    auth->token_count--;
    return body;
}
