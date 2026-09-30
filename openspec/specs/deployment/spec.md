# Deployment

## Purpose

Provide a Render deployment configuration for the Autonomous Incident Triage Agent, including health checks, environment-based secrets, and persistence of paused approvals across cold starts.

## Requirements

### Requirement: Render deployment

The service SHALL bind to the port provided in $PORT.

#### Scenario: Render starts the service

- **GIVEN** the service is deployed on Render
- **WHEN** Render provides a $PORT environment variable
- **THEN** the application SHALL bind to that port

### Requirement: Secret management

Secrets SHALL come only from environment variables; .env SHALL NOT be committed.

#### Scenario: Environment secrets

- **GIVEN** the application requires GEMINI_API_KEY or DATABASE_URL
- **WHEN** the application starts
- **THEN** the values SHALL be read from environment variables
- **AND** .env SHALL NOT be tracked by git

### Requirement: Health check

GET /healthz SHALL return 200 without calling Gemini or the database.

#### Scenario: Health check

- **GIVEN** the application is running
- **WHEN** GET /healthz is requested
- **THEN** it SHALL return HTTP 200
- **AND** it SHALL not require Gemini or database access

### Requirement: Approval persistence

A paused approval SHALL still be resumable after a cold start.

#### Scenario: Resume after cold start

- **GIVEN** an approval is paused
- **WHEN** the Render service experiences a cold start
- **THEN** the paused approval SHALL remain resumable
