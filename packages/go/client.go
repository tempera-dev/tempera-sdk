package tempera

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
)

const Version = "0.12.0"

type RequestSpec struct {
	Product   string
	Operation string
	Method    string
	URL       string
	Headers   http.Header
	Body      []byte
}

type APIError struct {
	Status    int
	Code      string
	Message   string
	RequestID string
	Product   string
	Operation string
	Body      any
}

func (e *APIError) Error() string { return fmt.Sprintf("Tempera %s.%s failed (%d): %s", e.Product, e.Operation, e.Status, e.Message) }

type Client struct {
	HTTP                *http.Client
	BaseURLs            map[string]string
	Bearers             map[string]string
	AccountToken        string
	IntrospectionSecret string
}

func NewClient() *Client {
	return &Client{HTTP: http.DefaultClient, BaseURLs: map[string]string{}, Bearers: map[string]string{}}
}

func (c *Client) BuildRequest(product, operation string, params map[string]any) (RequestSpec, error) {
	op, ok := FindOperation(product, operation)
	if !ok { return RequestSpec{}, fmt.Errorf("unknown Tempera operation: %s.%s", product, operation) }
	p, ok := Products[product]
	if !ok { return RequestSpec{}, fmt.Errorf("unknown Tempera product: %s", product) }
	base := strings.TrimRight(c.BaseURLs[product], "/")
	if base == "" { return RequestSpec{}, fmt.Errorf("missing base URL for %s; set %s or BaseURLs[%q]", product, p.EnvVar, product) }

	path := op.Path
	consumed := map[string]bool{}
	for _, name := range op.PathParams {
		value, exists := params[name]
		if !exists || fmt.Sprint(value) == "" { return RequestSpec{}, fmt.Errorf("%s.%s: missing required path parameter %q", product, operation, name) }
		path = strings.ReplaceAll(path, "{"+name+"}", url.PathEscape(fmt.Sprint(value)))
		consumed[name] = true
	}

	query := url.Values{}
	for _, name := range op.Query {
		if value, exists := params[name]; exists && value != nil {
			query.Set(name, fmt.Sprint(value)); consumed[name] = true
		} else if contains(op.RequiredQuery, name) {
			return RequestSpec{}, fmt.Errorf("%s.%s: missing required query parameter %q", product, operation, name)
		}
	}

	body := map[string]any{}
	for key, value := range op.BodyDefaults { body[key] = value }
	for _, name := range op.Body {
		if value, exists := params[name]; exists { body[name] = value; consumed[name] = true }
		if contains(op.RequiredBody, name) {
			if value, exists := params[name]; !exists || value == nil { return RequestSpec{}, fmt.Errorf("%s.%s: missing required body field %q", product, operation, name) }
		}
	}
	for _, name := range op.ForbiddenBody {
		if _, exists := params[name]; exists { return RequestSpec{}, fmt.Errorf("%s.%s: %s is derived from the authenticated principal", product, operation, name) }
	}
	for key, value := range params {
		if consumed[key] { continue }
		if op.Method == "GET" || op.Method == "DELETE" { query.Set(key, fmt.Sprint(value)) } else { body[key] = value }
	}

	headers := make(http.Header)
	headers.Set("Accept", "application/json")
	bearer, err := c.bearer(product, op)
	if err != nil { return RequestSpec{}, err }
	if bearer != "" { headers.Set("Authorization", "Bearer "+bearer) }

	var encoded []byte
	if len(body) > 0 {
		encoded, err = json.Marshal(body); if err != nil { return RequestSpec{}, err }
		headers.Set("Content-Type", "application/json")
	}
	full := base + path
	if q := query.Encode(); q != "" { full += "?" + q }
	return RequestSpec{Product: product, Operation: operation, Method: op.Method, URL: full, Headers: headers, Body: encoded}, nil
}

func (c *Client) bearer(product string, op OperationSpec) (string, error) {
	switch op.Auth {
	case "none": return "", nil
	case "account": if c.AccountToken == "" { return "", errors.New("account token required") }; return c.AccountToken, nil
	case "introspectionSecret": if c.IntrospectionSecret == "" { return "", errors.New("introspection secret required") }; return c.IntrospectionSecret, nil
	default:
		audience := op.AuthAudience
		if audience == "" { audience = Products[product].Audience }
		if token := c.Bearers[audience]; token != "" { return token, nil }
		return "", fmt.Errorf("missing credential for %s audience %s", product, audience)
	}
}

func (c *Client) Do(ctx context.Context, product, operation string, params map[string]any, out any) error {
	spec, err := c.BuildRequest(product, operation, params); if err != nil { return err }
	req, err := http.NewRequestWithContext(ctx, spec.Method, spec.URL, bytes.NewReader(spec.Body)); if err != nil { return err }
	req.Header = spec.Headers.Clone()
	resp, err := c.HTTP.Do(req); if err != nil { return err }
	defer resp.Body.Close()
	payload, err := io.ReadAll(io.LimitReader(resp.Body, 16<<20)); if err != nil { return err }
	var decoded any
	if len(payload) > 0 { _ = json.Unmarshal(payload, &decoded) }
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		code, message, requestID := normalizeError(decoded, resp.Status)
		if requestID == "" { requestID = resp.Header.Get("x-request-id") }
		return &APIError{Status: resp.StatusCode, Code: code, Message: message, RequestID: requestID, Product: product, Operation: operation, Body: decoded}
	}
	if out != nil && len(payload) > 0 { return json.Unmarshal(payload, out) }
	return nil
}

func normalizeError(body any, fallback string) (string, string, string) {
	root, _ := body.(map[string]any)
	if raw, ok := root["error"]; ok {
		if e, ok := raw.(map[string]any); ok {
			code, _ := e["status"].(string); if code == "" { code, _ = e["code"].(string) }
			message, _ := e["message"].(string); if message == "" { message = fallback }
			requestID, _ := e["requestId"].(string); if requestID == "" { requestID, _ = e["request_id"].(string) }
			return code, message, requestID
		}
		if text, ok := raw.(string); ok { if msg, ok := root["message"].(string); ok { return text, msg, "" }; return "", text, "" }
	}
	return "", fallback, ""
}

func contains(values []string, value string) bool { for _, item := range values { if item == value { return true } }; return false }
