# Tempera producer contract standard v1

Every Tempera product that exposes an HTTP API publishes exactly one machine
contract, in one place, in one format. The SDK, the MCP gateway, and Workflows
all consume that one file. This document is the normative definition; the
enforcing implementation is `scripts/lint_producer_contract.py`, vendored into
every producer repository at `.tempera/agent-kit/scripts/lint_producer_contract.py`.

## 1. One file, one path, one format

| Property | Required value |
| --- | --- |
| Path in the producer repository | `contracts/openapi/<product>.openapi.json` |
| `<product>` | the producer repository name with no `tempera-` prefix, kebab-case |
| Format | OpenAPI **3.1.0**, JSON |
| Serialization | `json.dumps(document, indent=2, ensure_ascii=False)` plus one trailing newline |
| Key order | whatever the producer's builder emits; the linter never reorders |

`openapi` MUST be the exact string `3.1.0`. 3.0.x documents are upgraded, not
tolerated: 3.1.0 is the first release whose schema dialect is JSON Schema
2020-12, which is what every downstream generator already assumes. Upgrading
is not a version-string edit: `nullable: true` becomes a type union or an
`anyOf` with `"null"`, and `exclusiveMinimum`/`exclusiveMaximum` become
numbers rather than booleans.

Every local `$ref` MUST resolve inside the document. A contract can satisfy
every rule below and still be unusable: `tempera-connectors` published four
references to components it never defined, because utoipa emits the literal
type path written in the annotation, and nothing noticed until the SDK tried
to derive typed operations from it.

The file MUST be reproducible. A producer whose contract is emitted from server
code publishes a regeneration entry point; a producer whose contract is
hand-written publishes a drift gate that compares the contract to the routes the
server actually serves. Either way `scripts/regen-contract.sh --check` exits
non-zero when the committed file does not match the running service.

## 2. Errors are `google.rpc.Status`, everywhere

Every non-2xx response in every operation MUST reference the shared component:

```json
{"$ref": "#/components/responses/Error"}
```

`components.responses.Error` and `components.schemas.Status` are byte-identical
across all producers; the linter compares them to the canonical copy in
`contracts/status-component.json`. The wire body is:

```json
{
  "error": {
    "code": 400,
    "status": "INVALID_ARGUMENT",
    "message": "Human readable, safe to show a developer.",
    "details": []
  }
}
```

`code` is the integer HTTP status. `status` is the canonical AIP-193 enum name.
`message` is a string. `details` is an array, possibly empty. No producer may
add a sibling of `error`, and no producer may return a bare `{"detail": ...}`
or `{"message": ...}` envelope.

## 3. Naming and shape (AIP)

These are enforced mechanically. There is no backward-compatibility exemption:
these APIs have no external consumers, so a rename is a rename.

| Rule | Requirement | AIP |
| --- | --- | --- |
| `aip-127-versioned-path` | Resource paths begin `/v1/`. Health and transport routes are declared exceptions, not violations. | [127](https://google.aip.dev/127) |
| `aip-127-no-put` | No `PUT`. Full replacement is `PATCH` with `updateMask`. | [127](https://google.aip.dev/127) |
| `aip-127-lower-camel-parameters` | Every path and query parameter name is lowerCamelCase. | [127](https://google.aip.dev/127) |
| `aip-127-lower-camel-json-fields` | Every request and response JSON field name is lowerCamelCase. | [127](https://google.aip.dev/127) |
| `aip-136-lower-camel-custom-verb` | Custom methods are `:lowerCamelVerb` suffixes on a collection or resource. | [136](https://google.aip.dev/136) |
| `aip-158-list-pagination` | Every `List` method accepts `pageSize` and `pageToken` and returns `nextPageToken`. | [158](https://google.aip.dev/158) |
| `aip-161-update-mask` | Every `PATCH` accepts `updateMask`. | [161](https://google.aip.dev/161) |
| `aip-122-resource-names` | Collection segments are lowerCamelCase plurals. No `snake_case`, no `kebab-case`. | [122](https://google.aip.dev/122) |
| `aip-193-standard-errors` | Section 2 above. | [193](https://google.aip.dev/193) |

Health and transport routes (`/healthz`, `/readyz`, `/livez`, `/metrics`,
`/mcp`, `/.well-known/*`, OAuth endpoints, webhook receivers, OTLP ingest,
bidirectional streams) are exempt from the path and error rules and MUST be
declared in `x-tempera-protocol-routes` at the document root:

```json
"x-tempera-protocol-routes": ["/healthz", "/readyz", "/mcp"]
```

An undeclared route gets no exemption. A declared route that does not exist is
an error. And only health, transport and identity-protocol shapes may be
declared at all — a `/v1/...` resource path is refused even when it is listed,
which is what stops the exemption list from becoming a dumping ground.

Health probes are served at `/healthz` and `/readyz`, not under `/v1`. That is
not a style preference: a versioned health route is a resource path, so it
cannot be exempted, and the rename is the only way to stop carrying a
permanent violation. Data Engine, Payments and Document all moved for this
reason; Gym, LLM, Workflows, Clearing and Connectors were already there.

The aggregate ratchet in `tempera-sdk` reads this declaration rather than
keeping its own table, and re-validates it. A producer's exemption list and
the SDK's cannot drift apart because there is only one.

## 4. Required `x-tempera-*` extensions

Every operation MUST declare:

| Extension | Type | Meaning |
| --- | --- | --- |
| `x-tempera-auth-kind` | `none` \| `account` \| `product` \| `oauthResource` \| `introspectionSecret` | which credential the SDK attaches |
| `x-tempera-auth-audience` | string | required exactly when `auth-kind` is `oauthResource`; must be a registered audience |
| `x-tempera-required-scope` | string | the single scope the route demands, or omitted when `auth-kind` is `none` |

Operations that change physical or financial state MUST additionally declare:

| Extension | Type | Meaning |
| --- | --- | --- |
| `x-tempera-physical-action` | boolean | the call has an effect outside the database |
| `x-tempera-prepare-commit-required` | boolean | the effect is only reachable through prepare/commit; implies `physical-action` |

Operations addressing a resource by name MUST declare the AIP-122 pattern:

| Extension | Type | Meaning |
| --- | --- | --- |
| `x-tempera-resource-pattern` | object | maps a path parameter to its pattern, e.g. `{"parent": "projects/*"}` |

## 5. Publication and propagation

A producer merge to `main` that touches the contract path MUST fire a
`repository_dispatch` of type `tempera-contract-updated` at `tempera-dev/tempera-sdk`
with `{"product": "<sdkKey>", "commit": "<40-hex>"}`. The SDK's receiver
re-vendors at that exact commit, regenerates every language surface, runs the
gates, and opens a pull request. No human copies a spec between repositories.

The agent kit distributes that workflow as `.github/workflows/notify-sdk.yml`,
byte-identical everywhere. It cannot fire yet: sending a dispatch needs write
access to `tempera-sdk`, and the only app installed org-wide is read-only, so
the workflow skips with an explanation rather than reddening every producer's
build. Until an organization administrator creates a write-scoped notifier app
and publishes `TEMPERA_CONTRACT_NOTIFIER_CLIENT_ID` and
`TEMPERA_CONTRACT_NOTIFIER_PRIVATE_KEY`, the SDK's three-hourly sweep
re-vendors from each producer's `main` on its own, so propagation is delayed
rather than lost.

The SDK pins each vendored contract with a `.source` lock recording the source
repository, branch, 40-character commit, path, git blob SHA, SHA-256, and the
generator version. Vendoring at a branch name, a tag, or a short SHA is refused.
