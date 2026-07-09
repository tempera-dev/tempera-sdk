#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Product {
    pub name: &'static str,
    pub repository: &'static str,
    pub env: &'static str,
}

pub const SCOPES: &[&str] = &[
    "mcp:invoke",
    "trace:read",
    "trace:write",
    "dataset:read",
    "dataset:write",
    "eval:run",
    "pii:unmask",
    "admin",
];

pub const AUTH_HUB: Product = Product {
    name: "auth-hub",
    repository: "https://github.com/tempera-dev/auth-hub",
    env: "TEMPERA_CONTROL_PLANE_URL",
};

pub const TEMP_JS: Product = Product {
    name: "temp.js",
    repository: "https://github.com/tempera-dev/temp.js",
    env: "TEMPERA_TEMPJS_URL",
};

pub const TEMPO: Product = Product {
    name: "tempo",
    repository: "https://github.com/tempera-dev/tempo",
    env: "TEMPERA_TEMPO_URL",
};

pub const TEMP_OS: Product = Product {
    name: "tempOS",
    repository: "https://github.com/tempera-dev/tempOS",
    env: "TEMPERA_TEMPOS_URL",
};

pub const REMI: Product = Product {
    name: "remi",
    repository: "https://github.com/tempera-dev/remi",
    env: "TEMPERA_REMI_URL",
};

pub const CRADLE: Product = Product {
    name: "cradle",
    repository: "https://github.com/tempera-dev/cradle",
    env: "TEMPERA_CRADLE_URL",
};

pub const ARRHA: Product = Product {
    name: "Arrha",
    repository: "https://github.com/tempera-dev/arrha",
    env: "TEMPERA_ARRHA_URL",
};

pub const PRODUCTS: &[Product] = &[AUTH_HUB, TEMPO, TEMP_JS, TEMP_OS, REMI, CRADLE, ARRHA];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ApiTargets {
    pub public_site_url: &'static str,
    pub control_plane_url: &'static str,
    pub auth_issuer_url: &'static str,
    pub auth_jwks_url: &'static str,
    pub palette_api_url: &'static str,
    pub palette_mcp_url: &'static str,
    pub tempo_api_url: &'static str,
}

pub const PRODUCTION_TARGETS: ApiTargets = ApiTargets {
    public_site_url: "https://tempera.dev",
    control_plane_url: "https://api.tempera.dev",
    auth_issuer_url: "https://api.tempera.dev",
    auth_jwks_url: "https://api.tempera.dev/.well-known/jwks.json",
    palette_api_url: "https://mcp.tempera.dev",
    palette_mcp_url: "https://mcp.tempera.dev/mcp",
    tempo_api_url: "https://tempo.tempera.dev",
};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClientConfig {
    pub access_token: Option<String>,
    pub endpoints: Vec<(&'static str, String)>,
}

impl ClientConfig {
    pub fn new() -> Self {
        Self {
            access_token: None,
            endpoints: Vec::new(),
        }
    }

    pub fn with_bearer_token(mut self, token: impl Into<String>) -> Self {
        self.access_token = Some(token.into());
        self
    }
}

impl Default for ClientConfig {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exports_aggregated_product_surface() {
        assert!(PRODUCTS.iter().any(|product| product.name == "temp.js"));
        assert!(PRODUCTS.iter().any(|product| product.name == "tempo"));
        assert!(PRODUCTS.iter().any(|product| product.name == "tempOS"));
        assert!(PRODUCTS.iter().any(|product| product.name == "remi"));
        assert!(PRODUCTS.iter().any(|product| product.name == "cradle"));
        assert!(PRODUCTS.iter().any(|product| product.name == "Arrha"));
        assert!(SCOPES.contains(&"mcp:invoke"));
        assert!(SCOPES.contains(&"admin"));
        assert_eq!(PRODUCTION_TARGETS.control_plane_url, "https://api.tempera.dev");
        assert_eq!(PRODUCTION_TARGETS.palette_mcp_url, "https://mcp.tempera.dev/mcp");
        assert_eq!(PRODUCTION_TARGETS.tempo_api_url, "https://tempo.tempera.dev");
    }

    #[test]
    fn carries_bearer_token_config() {
        let config = ClientConfig::new().with_bearer_token("token_123");
        assert_eq!(config.access_token.as_deref(), Some("token_123"));
    }
}
