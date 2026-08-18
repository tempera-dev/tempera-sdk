package tempera

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strings"
)

const Version = "0.12.0"

type RequestSpec struct {
	Product   string
	Operation string
	Method    string
	URL       string
	Headers   http.Header
	Body      []byte
}

type APIError struct {
	Status    int
	Code      string
	Message   string
	RequestID string
	Product   string
	Operation string
	Body      any
}

func (e *APIError) Error() string {
	return fmt.Sprintf("Tempera %s.%s failed (%d): %s", e.Product, e.Operation, e.Status, e.Message)
}

type Client struct {
	HTTP                *http.Client
	BaseURLs            map[string]string
	Bearers             map[string]string
	AccountToken        string
	IntrospectionSecret string
}

func NewClient() *Client {
	return &Client{HTTP: http.DefaultClient, BaseURLs: map[string]string{}, Bearers: map[string]string{}}
}

func (c *Client) BuildRequest(product, operation string, params map[string]any) (RequestSpec, error) {
	op, ok := FindOperation(product, operation)
	if !ok {
		return RequestSpec{}, fmt.Errorf("unknown Tempera operation: %s.%s", product, operation)
	}
	p, ok := Products[product]
	if !ok {
		return RequestSpec{}, fmt.Errorf("unknown Tempera product: %s", product)
	}
	base := strings.TrimRight(c.BaseURLs[product], "/")
	if base == "" {
		return RequestSpec{}, fmt.Errorf("missing base URL for %s; set %s or BaseURLs[%q]", product, p.EnvVar, product)
	}
	params = cloneParams(params)
	path := op.Path
	consumed := map[string]bool{}

	for _, name := range op.PathParams {
		value, source, exists, err := declaredParam(params, name)
		if err != nil {
			return RequestSpec{}, fmt.Errorf("%s.%s: %w", product, operation, err)
		}
		if !exists || value == nil || fmt.Sprint(value) == "" {
			return RequestSpec{}, fmt.Errorf("%s.%s: missing required path parameter %q", product, operation, name)
		}
		raw := fmt.Sprint(value)
		replacement := url.PathEscape(raw)
		if pattern := op.PathParamTemplates[name]; pattern != "" {
			var valid bool
			replacement, valid = expandAIPResourceName(raw, pattern)
			if !valid {
				return RequestSpec{}, fmt.Errorf("%s.%s: path parameter %q must match AIP resource pattern %q", product, operation, name, pattern)
			}
		}
		path = strings.ReplaceAll(path, "{"+name+"}", replacement)
		consumed[source] = true
	}

	query := url.Values{}
	for _, name := range op.Query {
		value, source, exists, err := declaredParam(params, name)
		if err != nil {
			return RequestSpec{}, fmt.Errorf("%s.%s: %w", product, operation, err)
		}
		if exists && value != nil {
			query.Set(name, fmt.Sprint(value))
			consumed[source] = true
		} else if contains(op.RequiredQuery, name) {
			return RequestSpec{}, fmt.Errorf("%s.%s: missing required query parameter %q", product, operation, name)
		}
	}

	for _, name := range op.ForbiddenBody {
		_, _, exists, err := declaredParam(params, name)
		if err != nil {
			return RequestSpec{}, fmt.Errorf("%s.%s: %w", product, operation, err)
		}
		if exists {
			return RequestSpec{}, fmt.Errorf("%s.%s: %s is derived from the authenticated principal", product, operation, name)
		}
	}

	var encoded []byte
	body := map[string]any{}
	if op.RequestBodyKind == "binary" {
		value, source, exists, err := declaredParam(params, "content")
		if err != nil {
			return RequestSpec{}, fmt.Errorf("%s.%s: %w", product, operation, err)
		}
		if !exists {
			return RequestSpec{}, fmt.Errorf("%s.%s: missing binary content", product, operation)
		}
		switch v := value.(type) {
		case []byte:
			encoded = append([]byte(nil), v...)
		case string:
			encoded = []byte(v)
		default:
			return RequestSpec{}, fmt.Errorf("%s.%s: binary content must be []byte or string", product, operation)
		}
		consumed[source] = true
	} else {
		for key, value := range op.BodyDefaults {
			body[key] = value
		}
		for _, name := range op.Body {
			value, source, exists, err := declaredParam(params, name)
			if err != nil {
				return RequestSpec{}, fmt.Errorf("%s.%s: %w", product, operation, err)
			}
			if exists {
				body[name] = value
				consumed[source] = true
			}
			if contains(op.RequiredBody, name) && (!exists || value == nil) {
				return RequestSpec{}, fmt.Errorf("%s.%s: missing required body field %q", product, operation, name)
			}
		}
	}

	for key, value := range params {
		if consumed[key] || value == nil {
			continue
		}
		if op.Method == "GET" || op.Method == "DELETE" {
			query.Set(key, fmt.Sprint(value))
		} else if op.RequestBodyKind != "binary" {
			body[key] = value
		} else {
			return RequestSpec{}, fmt.Errorf("%s.%s: binary operations only accept content plus declared path/query parameters", product, operation)
		}
	}

	headers := make(http.Header)
	headers.Set("Accept", "application/json")
	bearer, err := c.bearer(product, op)
	if err != nil {
		return RequestSpec{}, err
	}
	if bearer != "" {
		headers.Set("Authorization", "Bearer "+bearer)
	}
	if op.RequestBodyKind == "binary" {
		if op.RequestContentType != "" {
			headers.Set("Content-Type", op.RequestContentType)
		}
	} else if len(body) > 0 {
		encoded, err = json.Marshal(body)
		if err != nil {
			return RequestSpec{}, err
		}
		headers.Set("Content-Type", "application/json")
	}
	full := base + path
	if q := query.Encode(); q != "" {
		full += "?" + q
	}
	return RequestSpec{Product: product, Operation: operation, Method: op.Method, URL: full, Headers: headers, Body: encoded}, nil
}

func (c *Client) bearer(product string, op OperationSpec) (string, error) {
	switch op.Auth {
	case "none":
		return "", nil
	case "account":
		if c.AccountToken == "" {
			return "", errors.New("account token required")
		}
		return c.AccountToken, nil
	case "introspectionSecret":
		if c.IntrospectionSecret == "" {
			return "", errors.New("introspection secret required")
		}
		return c.IntrospectionSecret, nil
	default:
		audience := op.AuthAudience
		if audience == "" {
			audience = Products[product].Audience
		}
		if token := c.Bearers[audience]; token != "" {
			return token, nil
		}
		return "", fmt.Errorf("missing credential for %s audience %s", product, audience)
	}
}

func (c *Client) Do(ctx context.Context, product, operation string, params map[string]any, out any) error {
	spec, err := c.BuildRequest(product, operation, params)
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, spec.Method, spec.URL, bytes.NewReader(spec.Body))
	if err != nil {
		return err
	}
	req.Header = spec.Headers.Clone()
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	payload, err := io.ReadAll(io.LimitReader(resp.Body, 16<<20))
	if err != nil {
		return err
	}
	var decoded any
	if len(payload) > 0 {
		_ = json.Unmarshal(payload, &decoded)
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		code, message, requestID := normalizeError(decoded, resp.Status)
		if requestID == "" {
			requestID = resp.Header.Get("x-request-id")
		}
		return &APIError{Status: resp.StatusCode, Code: code, Message: message, RequestID: requestID, Product: product, Operation: operation, Body: decoded}
	}
	if out != nil && len(payload) > 0 {
		return json.Unmarshal(payload, out)
	}
	return nil
}

func normalizeError(body any, fallback string) (string, string, string) {
	root, _ := body.(map[string]any)
	if raw, ok := root["error"]; ok {
		if e, ok := raw.(map[string]any); ok {
			code, _ := e["status"].(string)
			if code == "" {
				code, _ = e["code"].(string)
			}
			message, _ := e["message"].(string)
			if message == "" {
				message = fallback
			}
			requestID, _ := e["requestId"].(string)
			if requestID == "" {
				requestID, _ = e["request_id"].(string)
			}
			return code, message, requestID
		}
		if text, ok := raw.(string); ok {
			if msg, ok := root["message"].(string); ok {
				return text, msg, ""
			}
			return "", text, ""
		}
	}
	return "", fallback, ""
}

func declaredParam(params map[string]any, wire string) (any, string, bool, error) {
	alias := snakeAlias(wire)
	wireValue, hasWire := params[wire]
	aliasValue, hasAlias := params[alias]
	if alias != wire && hasWire && hasAlias {
		return nil, "", false, fmt.Errorf("pass either %q or its snake_case alias %q, not both", wire, alias)
	}
	if hasWire {
		return wireValue, wire, true, nil
	}
	if hasAlias {
		return aliasValue, alias, true, nil
	}
	return nil, "", false, nil
}

var acronymBoundary = regexp.MustCompile(`([A-Z]+)([A-Z][a-z])`)
var lowerUpperBoundary = regexp.MustCompile(`([a-z0-9])([A-Z])`)

func snakeAlias(value string) string {
	value = acronymBoundary.ReplaceAllString(value, `${1}_${2}`)
	value = lowerUpperBoundary.ReplaceAllString(value, `${1}_${2}`)
	return strings.ToLower(value)
}

func expandAIPResourceName(value, pattern string) (string, bool) {
	wanted := strings.Split(pattern, "/")
	got := strings.Split(value, "/")
	if len(wanted) != len(got) {
		return "", false
	}
	encoded := make([]string, len(got))
	for i := range wanted {
		if wanted[i] == "*" {
			if got[i] == "" || got[i] == "." || got[i] == ".." {
				return "", false
			}
			encoded[i] = url.PathEscape(got[i])
		} else {
			if wanted[i] != got[i] {
				return "", false
			}
			encoded[i] = wanted[i]
		}
	}
	return strings.Join(encoded, "/"), true
}

func cloneParams(values map[string]any) map[string]any {
	out := map[string]any{}
	for key, value := range values {
		out[key] = value
	}
	return out
}

func contains(values []string, value string) bool {
	for _, item := range values {
		if item == value {
			return true
		}
	}
	return false
}
