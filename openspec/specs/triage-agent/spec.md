# triage-agent Specification

## Purpose
Executes autonomous incident investigation by diagnosing backend service health, searching vector runbooks, and synthesizing incident reports with recommended remediations.

## Requirements

### Requirement: Service Health Inspection Tool
The agent SHALL provide a health check tool that accepts a target service name (`auth`, `database`, `payments`) and returns current service status, CPU/memory usage metrics, and error rates.

#### Scenario: Healthy Service Inspection
- **GIVEN** the target service is operational
- **WHEN** the health check tool is called with service name `auth`
- **THEN** it MUST return status `healthy` with normal CPU and memory metrics

#### Scenario: Degraded Service Inspection
- **GIVEN** a degraded backend condition (e.g. database high latency)
- **WHEN** the health check tool is called with service name `database`
- **THEN** it MUST return status `degraded` or `error` with latency or resource exhaustion metrics

### Requirement: Runbook Retrieval Tool
The agent SHALL provide a runbook retriever tool that queries the `incident_docs` table via `match_incident_docs` with query embedding vectors and returns matching runbook title, content, and similarity scores.

#### Scenario: Relevant Runbook Retrieval
- **GIVEN** an incident complaint regarding 504 timeouts on auth service
- **WHEN** the runbook retriever tool is invoked
- **THEN** it MUST return matching remediation steps from the seeded auth runbook

### Requirement: Agent State Graph & Reasoning
The agent SHALL orchestrate triage using a LangGraph state machine. It SHALL receive an incident complaint, execute health checks and runbook search, synthesize findings via Gemini LLM reasoning, and output an incident report containing root cause diagnosis and recommended remediation. If manual intervention is required, it SHALL set `requires_escalation: True` in the agent state.

#### Scenario: Self-Remediable Incident Triage
- **GIVEN** an incident complaint where health checks pass and runbook specifies self-remediation
- **WHEN** the LangGraph agent executes triage
- **THEN** it MUST output an incident report and set `requires_escalation: False`

#### Scenario: Escalation-Required Incident Triage
- **GIVEN** an incident complaint where a core service stays degraded and requires manual intervention
- **WHEN** the LangGraph agent executes triage
- **THEN** it MUST synthesize the diagnosis and set `requires_escalation: True`
