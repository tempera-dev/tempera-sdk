//! Browser-task ergonomics for the HTTP-less Rust SDK.
//!
//! Rust intentionally does not execute the loop because this crate owns no HTTP
//! runtime. Instead it keeps session identity/state and emits the exact Tempo
//! `RequestSpec`s a caller needs to drive the same observe -> decide -> act loop
//! exposed directly by the TypeScript and Python SDKs.

use crate::{BuildError, ParamValue, RequestSpec, TemperaClient};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BrowserTaskState {
    Open,
    Closing,
    Closed,
}

pub struct BrowserTask<'a> {
    client: &'a TemperaClient,
    session_id: String,
    state: BrowserTaskState,
}

impl<'a> BrowserTask<'a> {
    pub fn attach(client: &'a TemperaClient, session_id: impl Into<String>) -> Self {
        Self {
            client,
            session_id: session_id.into(),
            state: BrowserTaskState::Open,
        }
    }

    pub fn create_request(
        client: &'a TemperaClient,
        params: &[(impl AsRef<str>, ParamValue)],
    ) -> Result<RequestSpec, BuildError> {
        let owned = params
            .iter()
            .map(|(key, value)| (key.as_ref(), value.clone()))
            .collect::<Vec<_>>();
        client.build_request("tempo", "create_session", &owned)
    }

    pub fn session_id(&self) -> &str {
        &self.session_id
    }

    pub fn state(&self) -> &BrowserTaskState {
        &self.state
    }

    fn session_params(&self, extra: &[(&str, ParamValue)]) -> Vec<(&str, ParamValue)> {
        let mut params = Vec::with_capacity(extra.len() + 1);
        params.push(("session_id", self.session_id.clone().into()));
        params.extend(extra.iter().cloned());
        params
    }

    pub fn observe_request(&self, extra: &[(&str, ParamValue)]) -> Result<RequestSpec, BuildError> {
        self.client
            .build_request("tempo", "observe_session", &self.session_params(extra))
    }

    pub fn act_batch_request(
        &self,
        actions_json: impl Into<String>,
        extra: &[(&str, ParamValue)],
    ) -> Result<RequestSpec, BuildError> {
        let mut params = self.session_params(extra);
        params.push(("actions", ParamValue::RawJson(actions_json.into())));
        self.client.build_request("tempo", "act_batch", &params)
    }

    pub fn close_request(&mut self, extra: &[(&str, ParamValue)]) -> Result<RequestSpec, BuildError> {
        self.state = BrowserTaskState::Closing;
        self.client
            .build_request("tempo", "close_session", &self.session_params(extra))
    }

    /// Mark a close request as accepted by the remote runtime.
    pub fn mark_closed(&mut self) {
        self.state = BrowserTaskState::Closed;
    }

    /// Mark a close request as failed before the remote session closed.
    pub fn reopen_after_close_failure(&mut self) {
        if self.state == BrowserTaskState::Closing {
            self.state = BrowserTaskState::Open;
        }
    }
}

/// Transport-neutral description of one deterministic workflow step.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BrowserWorkflowStep {
    pub name: String,
    pub operation: String,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct BrowserWorkflow {
    steps: Vec<BrowserWorkflowStep>,
}

impl BrowserWorkflow {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn push(mut self, name: impl Into<String>, operation: impl Into<String>) -> Self {
        self.steps.push(BrowserWorkflowStep {
            name: name.into(),
            operation: operation.into(),
        });
        self
    }

    pub fn steps(&self) -> &[BrowserWorkflowStep] {
        &self.steps
    }
}
