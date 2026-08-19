package tempera

import (
	"context"
	"errors"
	"fmt"
)

type BrowserTaskState string

const (
	BrowserTaskOpen    BrowserTaskState = "open"
	BrowserTaskClosing BrowserTaskState = "closing"
	BrowserTaskClosed  BrowserTaskState = "closed"
)

type BrowserTask struct {
	Client          *Client
	SessionID       string
	Owned           bool
	State           BrowserTaskState
	LastObservation map[string]any
	LastReceipt     map[string]any
}

type BrowserDecision struct {
	Actions   []any
	Done      bool
	Value     any
	ActParams map[string]any
}

type BrowserWorker func(context.Context, *BrowserTask, map[string]any, int) (BrowserDecision, error)

type BrowserRunOptions struct {
	MaxSteps           int
	InitialObservation map[string]any
	Close              bool
}

type BrowserLoopResult struct {
	Task        *BrowserTask
	Steps       int
	Observation map[string]any
	Receipt     map[string]any
	Value       any
}

func CreateBrowserTask(ctx context.Context, client *Client, params map[string]any) (*BrowserTask, error) {
	if client == nil {
		return nil, errors.New("BrowserTask requires a Client")
	}
	var session map[string]any
	if err := client.Do(ctx, "tempo", "createSession", cloneMap(params), &session); err != nil {
		return nil, err
	}
	id := firstString(session, "sessionId", "session_id", "id", "name")
	if id == "" {
		return nil, errors.New("tempo.createSession returned no session identifier")
	}
	return &BrowserTask{Client: client, SessionID: id, Owned: true, State: BrowserTaskOpen}, nil
}

func AttachBrowserTask(client *Client, sessionID string) (*BrowserTask, error) {
	if client == nil || sessionID == "" {
		return nil, errors.New("BrowserTask.attach requires client and sessionID")
	}
	return &BrowserTask{Client: client, SessionID: sessionID, State: BrowserTaskOpen}, nil
}

func (t *BrowserTask) assertOpen() error {
	if t == nil || t.State != BrowserTaskOpen {
		return fmt.Errorf("BrowserTask %s is %s", t.SessionID, t.State)
	}
	return nil
}

func (t *BrowserTask) sessionParams(params map[string]any) map[string]any {
	request := cloneMap(params)
	delete(request, "session_id")
	request["sessionId"] = t.SessionID
	return request
}

func (t *BrowserTask) Observe(ctx context.Context, params map[string]any) (map[string]any, error) {
	if err := t.assertOpen(); err != nil {
		return nil, err
	}
	var observation map[string]any
	if err := t.Client.Do(ctx, "tempo", "observe", t.sessionParams(params), &observation); err != nil {
		return nil, err
	}
	t.LastObservation = observation
	return observation, nil
}

func (t *BrowserTask) Act(ctx context.Context, actions []any, params map[string]any) (map[string]any, error) {
	if err := t.assertOpen(); err != nil {
		return nil, err
	}
	if len(actions) == 0 {
		return nil, errors.New("BrowserTask.Act requires non-empty actions")
	}
	request := t.sessionParams(params)
	delete(request, "actions")
	request["batch"] = actions
	var receipt map[string]any
	if err := t.Client.Do(ctx, "tempo", "actBatch", request, &receipt); err != nil {
		return nil, err
	}
	t.LastReceipt = receipt
	return receipt, nil
}

func (t *BrowserTask) Step(ctx context.Context, action any, params map[string]any) (map[string]any, error) {
	return t.Act(ctx, []any{action}, params)
}

func (t *BrowserTask) Run(ctx context.Context, worker BrowserWorker, options BrowserRunOptions) (result BrowserLoopResult, err error) {
	if worker == nil {
		return result, errors.New("BrowserTask.Run requires a worker")
	}
	if err = t.assertOpen(); err != nil {
		return result, err
	}
	maxSteps := options.MaxSteps
	if maxSteps == 0 {
		maxSteps = 50
	}
	if maxSteps < 1 {
		return result, errors.New("max steps must be positive")
	}
	if options.Close {
		defer func() {
			if t.State == BrowserTaskOpen {
				if closeErr := t.Close(ctx, nil); err == nil && closeErr != nil {
					err = closeErr
				}
			}
		}()
	}
	observation := options.InitialObservation
	if observation == nil {
		observation, err = t.Observe(ctx, nil)
		if err != nil {
			return result, err
		}
	}
	var value any
	steps := 0
	for steps < maxSteps {
		if err = ctx.Err(); err != nil {
			return result, err
		}
		decision, decideErr := worker(ctx, t, observation, steps)
		if decideErr != nil {
			return result, decideErr
		}
		if decision.Done && len(decision.Actions) == 0 {
			value = decision.Value
			break
		}
		if len(decision.Actions) == 0 {
			return result, errors.New("BrowserTask worker decision must contain non-empty actions or Done")
		}
		var receipt map[string]any
		receipt, err = t.Act(ctx, decision.Actions, decision.ActParams)
		if err != nil {
			return result, err
		}
		steps++
		value = decision.Value
		if decision.Done {
			break
		}
		observation = settledObservation(receipt)
		if observation == nil {
			observation, err = t.Observe(ctx, nil)
			if err != nil {
				return result, err
			}
		} else {
			t.LastObservation = observation
		}
	}
	return BrowserLoopResult{Task: t, Steps: steps, Observation: observation, Receipt: t.LastReceipt, Value: value}, nil
}

func (t *BrowserTask) Close(ctx context.Context, params map[string]any) error {
	if t.State == BrowserTaskClosed {
		return nil
	}
	if t.State != BrowserTaskOpen {
		return fmt.Errorf("BrowserTask %s is already closing", t.SessionID)
	}
	t.State = BrowserTaskClosing
	if err := t.Client.Do(ctx, "tempo", "closeSession", t.sessionParams(params), nil); err != nil {
		t.State = BrowserTaskOpen
		return err
	}
	t.State = BrowserTaskClosed
	return nil
}

type BrowserWorkflowStep struct {
	Name string
	Run  func(context.Context, *BrowserTask, map[string]any, int) (map[string]any, error)
}

type BrowserWorkflow struct {
	Task  *BrowserTask
	Steps []BrowserWorkflowStep
}

func NewBrowserWorkflow(task *BrowserTask) *BrowserWorkflow {
	return &BrowserWorkflow{Task: task}
}

func (w *BrowserWorkflow) Use(name string, run func(context.Context, *BrowserTask, map[string]any, int) (map[string]any, error)) *BrowserWorkflow {
	w.Steps = append(w.Steps, BrowserWorkflowStep{Name: name, Run: run})
	return w
}

func (w *BrowserWorkflow) Run(ctx context.Context, state map[string]any) (map[string]any, error) {
	if w.Task == nil {
		return nil, errors.New("BrowserWorkflow requires a BrowserTask")
	}
	out := cloneMap(state)
	for i, step := range w.Steps {
		if step.Run == nil {
			return nil, fmt.Errorf("workflow step %q has no handler", step.Name)
		}
		values, err := step.Run(ctx, w.Task, out, i)
		if err != nil {
			return nil, err
		}
		for key, value := range values {
			out[key] = value
		}
	}
	return out, nil
}

func settledObservation(receipt map[string]any) map[string]any {
	for _, key := range []string{"observation", "settledObservation", "settled_observation"} {
		if value, ok := receipt[key].(map[string]any); ok {
			return value
		}
	}
	return nil
}

func firstString(values map[string]any, keys ...string) string {
	for _, key := range keys {
		if value, ok := values[key].(string); ok && value != "" {
			return value
		}
	}
	return ""
}

func cloneMap(values map[string]any) map[string]any {
	out := map[string]any{}
	for key, value := range values {
		out[key] = value
	}
	return out
}
