use tempera_sdk::{ParamValue, TemperaAuth, TemperaClient};

#[test]
fn llm_request_preserves_null_tool_turns_and_named_choice() {
    let client = TemperaClient::new()
        .with_auth(TemperaAuth::new("https://issuer.example.test").with_api_key("fixture-key"))
        .with_base_url("tempera_llm", "http://127.0.0.1:8080");
    let messages = r#"[{"role":"assistant","content":null,"tool_calls":[{"id":"call_1","type":"function","function":{"name":"inspect","arguments":"{}"}}]},{"role":"tool","tool_call_id":"call_1","content":"{}"}]"#;
    let base = vec![
        ("model", ParamValue::from("gpt-4o-mini")),
        ("max_tokens", ParamValue::Int(64)),
        ("messages", ParamValue::RawJson(messages.into())),
    ];
    let omitted = client
        .build_request("tempera_llm", "create_chat_completion", &base)
        .unwrap();
    let body = omitted.body_json.unwrap();
    assert!(body.contains(messages));
    assert!(!body.contains("\"tools\":"));
    assert!(!body.contains("\"tool_choice\":"));
    for choice in [
        "null",
        r#"{"type":"function","function":{"name":"inspect"}}"#,
        "\"none\"",
    ] {
        let mut params = base.clone();
        params.push(("tools", ParamValue::RawJson("null".into())));
        params.push(("tool_choice", ParamValue::RawJson(choice.into())));
        let spec = client
            .build_request("tempera_llm", "create_chat_completion", &params)
            .unwrap();
        assert_eq!(spec.url, "http://127.0.0.1:8080/v1/chat/completions");
        assert_eq!(spec.method, "POST");
        assert!(
            spec.headers
                .contains(&("authorization".into(), "Bearer fixture-key".into()))
        );
        let body = spec.body_json.unwrap();
        assert!(body.contains(messages));
        assert!(body.contains("\"tools\":null"));
        assert!(body.contains(&format!("\"tool_choice\":{choice}")));
    }
}
