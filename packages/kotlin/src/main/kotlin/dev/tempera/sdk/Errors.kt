// Uniform Tempera SDK errors, shared in shape with the TypeScript, Python,
// Rust, and Swift packages (see `surface.json` `errorContract`).
//
// - TemperaSdkException: a configuration or usage mistake, caught before or
//   instead of a request (missing credential, unknown product, bad path
//   parameter).
// - TemperaApiException: an HTTP response error, normalized from the canonical
//   AIP-193 envelope and the supported compatibility shapes so callers always
//   read the same fields.
// - TemperaMcpException: a JSON-RPC error from the MCP gateway.
// - TemperaTransportException: the request never produced an HTTP response.

package dev.tempera.sdk

/** Base class for every error this package raises. */
public open class TemperaSdkException(
    message: String,
    cause: Throwable? = null,
) : RuntimeException(message, cause)

/** The request never produced an HTTP response (DNS, TLS, timeout, reset). */
public class TemperaTransportException(
    /** What the underlying transport reported. */
    public val detail: String,
    cause: Throwable? = null,
) : TemperaSdkException("Tempera connection failed: " + detail, cause)

/** A JSON-RPC error returned by the MCP gateway. */
public class TemperaMcpException(
    /** JSON-RPC error code; `0` when the response carried no integer code. */
    public val code: Int,
    /** The gateway's own message, without the `MCP error <code>:` prefix. */
    public val detail: String,
    /** The error's `data` member, when it carried one. */
    public val data: TemperaJson? = null,
) : TemperaSdkException("MCP error " + code + ": " + detail)

/** The uniform fields every Tempera error body normalizes to. */
public data class TemperaNormalizedError(
    /** Machine-readable code, when the wire shape carried one. */
    public val code: String?,
    /** Human-readable message; never empty. */
    public val message: String,
    /** AIP-193 `google.rpc.ErrorInfo` reason from `error.details[]`. */
    public val reason: String?,
    /** Server request id carried in the body. */
    public val requestId: String?,
)

/** An HTTP response error with the uniform Tempera error fields. */
public class TemperaApiException(
    /** HTTP status code of the failed response. */
    public val status: Int,
    /** Machine-readable error code, when the wire shape carried one. */
    public val code: String?,
    /** The full human-readable message, already labelled with product and operation. */
    public val detail: String,
    /**
     * AIP-193 `google.rpc.ErrorInfo` reason. Producers publish a closed reason
     * vocabulary, so this is the field to branch on.
     */
    public val reason: String?,
    /** Server request id, from the body or the `x-request-id` header. */
    public val requestId: String?,
    /** Product key that made the request. */
    public val product: String?,
    /** Operation id that made the request. */
    public val operation: String?,
    /** The parsed response body, when it was JSON. */
    public val body: TemperaJson?,
    /** The HTTP status text, kept so the error can be re-labelled later. */
    public val statusText: String,
) : TemperaSdkException(detail) {

    public companion object {
        /**
         * Return the AIP-193 `google.rpc.ErrorInfo` reason from an error's
         * `details[]`. The first detail carrying a string `reason` wins.
         */
        public fun errorInfoReason(error: TemperaJson): String? {
            val details = error["details"]?.asArray() ?: return null
            for (detail in details) {
                val reason = detail["reason"]?.asString()
                if (reason != null) return reason
            }
            return null
        }

        /**
         * Normalize any Tempera product error body into the uniform fields.
         *
         * Wire shapes handled (see `surface.json` `errorContract.wireShapes`):
         * - canonical resource API:
         *   `{"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "...", "details": []}}`
         * - legacy flat: `{"error": "<code>", "message": "<text>"}`
         * - legacy message-only: `{"error": "<human message>"}`
         * - legacy nested: `{"error": {"code", "message", "request_id"?, ...}}`
         * - anything else: the message is the HTTP status text, or
         *   `"request failed"` when that is empty.
         */
        public fun normalize(body: TemperaJson?, statusText: String = ""): TemperaNormalizedError {
            val error = body?.get("error")
            if (error is TemperaJson.Obj) {
                // `error.status` wins over `error.code` only when it is a
                // string: the canonical envelope puts the enum in `status` and
                // the integer HTTP code in `code`.
                val code = error["status"]?.asString() ?: error["code"]?.asString()
                val requestId =
                    error["requestId"]?.asString() ?: error["request_id"]?.asString()
                return TemperaNormalizedError(
                    code = code,
                    message = error["message"]?.asString() ?: statusText,
                    reason = errorInfoReason(error),
                    requestId = requestId,
                )
            }
            if (error is TemperaJson.Text) {
                val message = body?.get("message")?.asString()
                if (message != null) {
                    return TemperaNormalizedError(error.value, message, null, null)
                }
                return TemperaNormalizedError(null, error.value, null, null)
            }
            return TemperaNormalizedError(
                code = null,
                message = if (statusText.isEmpty()) "request failed" else statusText,
                reason = null,
                requestId = null,
            )
        }

        /**
         * Build one error from a failed HTTP response. `requestId` falls back
         * to the `x-request-id` response header.
         */
        public fun from(
            status: Int,
            statusText: String = "",
            headers: List<TemperaKeyValue> = emptyList(),
            body: TemperaJson? = null,
            product: String? = null,
            operation: String? = null,
        ): TemperaApiException {
            val normalized = normalize(body, statusText)
            val headerRequestId =
                headers.firstOrNull { it.key.lowercase() == "x-request-id" }?.value
            val label = listOfNotNull(product, operation).joinToString(".")
            val subject = if (label.isEmpty()) "request" else label
            return TemperaApiException(
                status = status,
                code = normalized.code,
                detail =
                    "Tempera " + subject + " failed (" + status + "): " + normalized.message,
                reason = normalized.reason,
                requestId = normalized.requestId ?: headerRequestId,
                product = product,
                operation = operation,
                body = body,
                statusText = statusText,
            )
        }
    }
}
