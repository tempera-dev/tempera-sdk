package tempera

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"testing"
)

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }

func TestEveryGeneratedOperationBuildsAgainstDeclaredContract(t *testing.T) {
	client := NewClient()
	for product, spec := range Products {
		client.BaseURLs[product] = "https://example.test"
		if spec.Audience != "" {
			client.Bearers[spec.Audience] = "token"
		}
	}
	client.AccountToken = "account"
	client.IntrospectionSecret = "secret"
	for product, ops := range Operations {
		for _, op := range ops {
			if op.AuthAudience != "" {
				client.Bearers[op.AuthAudience] = "token"
			}
			params := map[string]any{}
			for _, name := range op.PathParams {
				if pattern := op.PathParamTemplates[name]; pattern != "" {
					parts := strings.Split(pattern, "/")
					for i := range parts {
						if parts[i] == "*" {
							parts[i] = "x"
						}
					}
					params[name] = strings.Join(parts, "/")
				} else {
					params[name] = "x"
				}
			}
			for _, name := range op.RequiredQuery {
				params[name] = "x"
			}
			for _, name := range op.RequiredBody {
				params[name] = "x"
			}
			if op.RequestBodyKind == "binary" {
				params["content"] = []byte("x")
			}
			if _, err := client.BuildRequest(product, op.ID, params); err != nil {
				t.Fatalf("%s.%s: %v", product, op.ID, err)
			}
			if _, ok := FindOperation(product, op.SnakeID); !ok {
				t.Fatalf("snake alias missing: %s.%s", product, op.SnakeID)
			}
		}
	}
}

func TestAIPResourceNamesRejectMalformedAliases(t *testing.T) {
	for product, ops := range Operations {
		for _, op := range ops {
			for name, pattern := range op.PathParamTemplates {
				client := NewClient()
				client.BaseURLs[product] = "https://example.test"
				if audience := Products[product].Audience; audience != "" {
					client.Bearers[audience] = "token"
				}
				if op.AuthAudience != "" {
					client.Bearers[op.AuthAudience] = "token"
				}
				client.AccountToken = "account"
				client.IntrospectionSecret = "secret"
				params := map[string]any{}
				for _, pathName := range op.PathParams {
					if pathName == name {
						params[snakeAlias(pathName)] = "not-a-resource-name"
					} else {
						params[pathName] = "x"
					}
				}
				if _, err := client.BuildRequest(product, op.ID, params); err == nil {
					t.Fatalf("%s.%s accepted malformed %s for pattern %s", product, op.ID, name, pattern)
				}
			}
		}
	}
}

func TestCanonicalAIPErrorNormalization(t *testing.T) {
	client := NewClient()
	client.BaseURLs["tempo"] = "https://tempo.test"
	client.Bearers[Products["tempo"].Audience] = "token"
	client.HTTP = &http.Client{Transport: roundTripFunc(func(req *http.Request) (*http.Response, error) {
		body := `{"error":{"code":400,"status":"INVALID_ARGUMENT","message":"bad request","details":[],"requestId":"req-1"}}`
		return &http.Response{StatusCode: 400, Status: "400 Bad Request", Header: http.Header{"Content-Type": []string{"application/json"}}, Body: io.NopCloser(strings.NewReader(body))}, nil
	})}
	var out any
	err := client.Do(context.Background(), "tempo", "health", nil, &out)
	apiErr, ok := err.(*APIError)
	if !ok {
		t.Fatalf("expected APIError, got %T %v", err, err)
	}
	if apiErr.Code != "INVALID_ARGUMENT" || apiErr.Message != "bad request" || apiErr.RequestID != "req-1" {
		t.Fatalf("unexpected error: %#v", apiErr)
	}
}

func TestBrowserTaskReusesSettledObservation(t *testing.T) {
	var observeCalls, actionCalls int
	client := NewClient()
	client.BaseURLs["tempo"] = "https://tempo.test"
	client.Bearers[Products["tempo"].Audience] = "token"
	client.HTTP = &http.Client{Transport: roundTripFunc(func(req *http.Request) (*http.Response, error) {
		var payload map[string]any
		if req.Body != nil {
			_ = json.NewDecoder(req.Body).Decode(&payload)
		}
		var body string
		switch {
		case req.Method == "POST" && strings.Contains(req.URL.Path, "/sessions") && !strings.Contains(req.URL.Path, ":"):
			body = `{"sessionId":"s-1"}`
		case strings.Contains(req.URL.Path, ":observe") || strings.Contains(req.URL.Path, "/observation"):
			observeCalls++
			body = `{"revision":0}`
		case strings.Contains(req.URL.Path, ":act") || strings.Contains(req.URL.Path, "actions"):
			actionCalls++
			body = `{"settledObservation":{"revision":1}}`
		case req.Method == "DELETE" || strings.Contains(req.URL.Path, ":close"):
			body = `{}`
		default:
			body = `{}`
		}
		return &http.Response{StatusCode: 200, Status: "200 OK", Header: http.Header{"Content-Type": []string{"application/json"}}, Body: io.NopCloser(strings.NewReader(body))}, nil
	})}

	task, err := CreateBrowserTask(context.Background(), client, map[string]any{"url": "https://example.test"})
	if err != nil {
		t.Fatal(err)
	}
	_, err = task.Run(context.Background(), func(_ context.Context, _ *BrowserTask, _ map[string]any, step int) (BrowserDecision, error) {
		if step == 0 {
			return BrowserDecision{Actions: []any{map[string]any{"kind": "scroll", "y": 1}}}, nil
		}
		return BrowserDecision{Done: true}, nil
	}, BrowserRunOptions{MaxSteps: 3})
	if err != nil {
		t.Fatal(err)
	}
	if actionCalls != 1 {
		t.Fatalf("action calls=%d", actionCalls)
	}
	if observeCalls > 1 {
		t.Fatalf("settled observation was not reused; observe calls=%d", observeCalls)
	}
}
