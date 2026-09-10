// The generated Tempera SDK for Kotlin: one credential set, every product.
//
// `TemperaSurface` (generated from `surface.json`) is the whole API contract;
// `TemperaClient` turns an operation id and parameters into an HTTP request and
// a normalized response, and `TemperaMcpClient` speaks the unified MCP gateway.
// Nothing here is hand-written per product, and the package has no external
// dependencies: JDK 17's `java.net.http` and nothing else.
//
// ```kotlin
// val auth = TemperaAuth(issuerUrl = "https://api.tempera.dev", apiKey = apiKey)
// val client = TemperaClient(auth = auth, environment = "staging")
// val traces = client.palette.call("listTraces", mapOf("tenantId" to "acme"))
// ```

package dev.tempera.sdk

/** Package-level metadata. */
public object TemperaSdk {
    /**
     * Package version, kept in step with the TypeScript, Python, Rust, and
     * Swift packages.
     */
    public const val VERSION: String = "0.13.0"

    /** The `surface.json` schema version the generated tables came from. */
    public const val SURFACE_VERSION: Int = TemperaSurface.version
}
