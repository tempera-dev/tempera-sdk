// The generated Tempera SDK for Swift: one credential set, every product.
//
// `TemperaSurface` (generated from `surface.json`) is the whole API contract;
// `TemperaClient` turns an operation id and parameters into an HTTP request and
// a normalized response, and `TemperaMcpClient` speaks the unified MCP gateway.
// Nothing here is hand-written per product, and the package has no external
// dependencies: Foundation and URLSession only.
//
// ```swift
// let auth = try TemperaAuth(issuerUrl: "https://api.tempera.dev", apiKey: apiKey)
// let client = try TemperaClient(auth: auth, environment: "staging")
// let traces = try await client.palette.call("listTraces", ["tenantId": "acme"])
// ```

/// Package-level metadata.
public enum TemperaSDK {
    /// Package version, kept in step with the TypeScript, Python, Rust, and
    /// Kotlin packages.
    public static let version = "0.12.0"

    /// The `surface.json` schema version the generated tables came from.
    public static let surfaceVersion = TemperaSurface.version
}

extension TemperaClient {
    /// Every product accessor (generated in `Surface.swift`) goes through here;
    /// the key always exists in the generated product table, so the lookup
    /// cannot fail at runtime.
    nonisolated func productClient(_ key: String) -> TemperaProductClient {
        guard let spec = TemperaSurface.findProduct(key: key) else {
            preconditionFailure("generated product table lost \(key)")
        }
        return TemperaProductClient(spec: spec, client: self)
    }
}
