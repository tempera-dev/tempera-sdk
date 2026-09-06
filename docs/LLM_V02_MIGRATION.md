# LLM 0.2 contract intake

The LLM contract and source receipt pin merged producer
`5507fec7ce9fb25d47663d4f187a122f11b64c82`. Its OpenAPI version is 0.2.0.
The chat completion operation now declares `tools` and `tool_choice`; assistant
messages support nullable content, tool calls, and correlated tool results.

The gateway Rust crate intentionally changes its public struct constructors in
0.2.0. See that producer's `docs/tool-contract-v02-migration.md` for
`OpenAiNullable::{Missing, Null, Value}` and the added fields. This SDK does not
import those gateway structs: TypeScript and Python operations take generic JSON
payloads; Rust builds requests using `ParamValue` and an application-owned HTTP
transport. Generation here publishes operation metadata, not new typed message
DTOs. Existing SDK constructors are unchanged.

For TypeScript omit a property to omit it from JSON; use `null` for explicit null.
For Python omit the dictionary key or use `None`, respectively. For Rust omit the
parameter or use `ParamValue::RawJson("null".into())`; encode nested arrays/objects
as valid raw JSON, not string-valued parameters. Preserve assistant `tool_calls`
and each tool result's `tool_call_id` when passing conversation history.

Use the normal `createChatCompletion` / `create_chat_completion` operation with
an onboarding-provisioned credential and endpoint. A TOOLS phase may omit
`response_format`; a FINAL phase can omit tools, set `tool_choice` to `none`, and
request `response_format.type = json_schema`. The gateway still validates final
structured output. Wire serialization tests do not qualify real providers or
deployment authentication/usage storage. Workflows vendoring and curated MCP
admission require their own reviewed consumer changes after SDK acceptance.

## Local verification

Run `npm test` with Python 3.10 or newer on `PATH`. The suites cover SDK request
construction and transport serialization in all three languages. For an actual
TypeScript/Python HTTP round trip through the gateway, build the pinned LLM
producer and run:

```sh
python3 scripts/test-llm-producer-loopback.py --gateway-binary /absolute/path/to/tempera-llm
```

Record the supplied binary's source/build provenance with the output hash.
The runner starts only loopback services, uses a fixed test credential and
explicit unmetered fixture configuration, checks unauthenticated rejection,
and completes TOOLS then FINAL calls through both clients. Its provider is a
local mock. The Rust SDK remains HTTP-less; its test covers the request handed
to an application's own HTTP transport.
