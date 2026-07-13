use tempera_sdk::TemperaMcpClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let url = std::env::var("TEMPERA_MCP_URL")
        .unwrap_or_else(|_| "http://127.0.0.1:4419/mcp".into());
    let bearer = std::env::var("TEMPERA_MCP_TOKEN").unwrap_or_else(|_| "local-test".into());
    let client = TemperaMcpClient::connect(url, bearer).await?;
    let tools = client.list_tools().await?;
    let status = client.status().await?;
    println!(
        "{}",
        serde_json::json!({
            "tools": tools.len(),
            "status": status.structured_content,
        })
    );
    client.close().await?;
    Ok(())
}
