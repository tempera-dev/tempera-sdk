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
    }

    #[test]
    fn carries_bearer_token_config() {
        let config = ClientConfig::new().with_bearer_token("token_123");
        assert_eq!(config.access_token.as_deref(), Some("token_123"));
    }
}
