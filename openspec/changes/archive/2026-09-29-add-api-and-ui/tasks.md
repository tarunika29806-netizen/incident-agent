# Tasks

## 1. API service layer
- [ ] Create shared service functions for triage, approval, and rejection.
- [ ] Preserve LangGraph thread/checkpoint state.
- [ ] Map graph states to API workflow states.

## 2. FastAPI
- [ ] Add `/chat`.
- [ ] Add `/approve`.
- [ ] Add `/reject`.
- [ ] Add `/healthz`.
- [ ] Return HTTP 400 when no approval is pending.

## 3. Gradio UI
- [ ] Create the required input/output controls.
- [ ] Connect UI actions to the shared service layer.
- [ ] Mount Gradio at `/`.

## 4. Tests
- [ ] Test `/chat`.
- [ ] Test approval flow.
- [ ] Test rejection flow.
- [ ] Test HTTP 400 for missing approval.
- [ ] Test `/healthz`.
- [ ] Test Gradio/shared service integration.

## 5. Verification
- [ ] Run the complete pytest suite.
- [ ] Validate the OpenSpec change.
- [ ] Archive the completed change.
