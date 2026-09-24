# agenoscope — Architecture & Requirements Specification
**Mode: ARCHITECT** | Status: Draft for review before implementation begins

---

## 0. How to Read This Document

This is the MODE 1 (ARCHITECT) deliverable. No implementation code is included. It defines *what* is being built, *why*, and *how it will be traced from requirement to test*. Implementation (MODE 2) will proceed slice-by-slice against this document, and MODE 3 will verify against the acceptance criteria defined here.

Traceability chain used throughout:
`REQ → FEAT → SLICE → COMPONENT → API → DB → TEST → ACCEPTANCE CRITERIA`

---

## 1. Problem, Users, Goals, Constraints

### 1.1 Problem
AI agent developers cannot efficiently diagnose *why* an agent run failed (schema drift, context exhaustion, tool non-determinism, infinite loops, silent state loss). Existing tools (LangSmith, etc.) show traces but not root-cause diagnosis, and there is no memory of previously-resolved similar failures.

### 1.2 Users
- **U1 — Agent Developer**: builds/operates LangGraph or similar agents, uses LangSmith, wants fast root-cause diagnosis.
- **U2 — Team Lead / Reviewer**: approves proposed fixes (Human-in-the-Loop gate), wants an audit trail.
- (No end-user/consumer persona — this is a developer tool.)

### 1.3 Goals (MVP)
- G1: Ingest a failed agent run from LangSmith (primary) or via a custom SDK/webhook (fallback).
- G2: Automatically classify the failure type (Triage Agent).
- G3: Retrieve similar historically-resolved cases and draft a fix (Remediation Agent).
- G4: Present root cause + evidence + proposed patch clearly to the user.
- G5: Require explicit human approval before anything is considered "applied."
- G6: Store approved cases to improve future retrieval quality.
- G7: Never store or transmit the user's LLM provider key beyond the single request lifecycle (BYOK).

### 1.4 Constraints
- C1: BYOK — the system must not persist LLM provider API keys.
- C2: LangSmith is the primary integration; a custom SDK/webhook is a fallback ingestion path — both must produce the same internal `AgentRun` representation.
- C3: A vector store (Qdrant) is required for similarity search over past resolved cases — this is an explicitly justified exception to "avoid multiple databases," since full-text/relational similarity search cannot satisfy semantic case retrieval (REQ-006).
- C4: No automatic mutation of the user's agent/code — the system only *proposes*; approval is mandatory before a case is marked "applied." The MVP does **not** actually push code changes anywhere (see §9 Excluded Scope) — "applying" a fix in MVP means marking it accepted and recording it as a resolved case, not performing an automated code edit.
- C5: Single-tenant-per-user data isolation is mandatory (multi-user SaaS, not shared traces).

### 1.5 Assumptions
- A1: Users already have a LangSmith account and API key for their own project, OR are willing to instrument their agent with a small SDK/webhook call.
- A2: Users have their own LLM provider key (OpenAI/Anthropic/etc.) with sufficient quota to run the Triage + Remediation agents.
- A3: "Similar past cases" scope is per-user (or per-organization) — we do not build a cross-customer shared knowledge base in MVP (privacy).
- A4: Runs of interest are not extremely large (>~200 trace steps) in MVP; very large traces are summarized/truncated rather than fully embedded.

### 1.6 Ambiguities Requiring a Decision (resolved below, flagged for confirmation)
| # | Ambiguity | Resolution taken (MVP) | Rationale |
|---|---|---|---|
| AMB-1 | Does "applying" a fix mean agenoscope edits the user's source code? | **No.** Approval marks the case "Resolved/Approved" and stores the patch text as a reference artifact. Actual code application is manual (copy the diff) in MVP. | Avoids unsafe automated code mutation into third-party repos; matches "Human-in-the-Loop" language in the problem statement, which describes approval *before a change is applied*, not automated push. |
| AMB-2 | Is the custom SDK a push (webhook) or pull (polling) model? | **Push webhook** (`POST /api/v1/ingest/run`) plus a thin optional Python/JS SDK that wraps the HTTP call. | Simpler, no long-lived polling infrastructure, matches "lightweight." |
| AMB-3 | Is cross-user/global case similarity in scope? | **No, out of scope for MVP.** Similarity search is scoped to the requesting user's own org/workspace. | Stated privacy concern ("user keys are never stored"); extending to shared corpus is a privacy/consent decision for later. |
| AMB-4 | Single LLM provider or multiple? | Support **OpenAI and Anthropic** as BYOK providers in MVP via a provider-agnostic interface; adding more later is additive. | Covers the two most common providers without over-engineering a universal LLM abstraction on day one. |

If any of AMB-1..4 do not match actual intent, this must be corrected before MODE 2 begins — flagging per the Autonomy Rule ("materially different product interpretations").

---

## 2. Functional Requirements

| ID | Requirement |
|---|---|
| REQ-001 | User can authenticate and manage their account (signup/login, session). |
| REQ-002 | User can connect a LangSmith project by supplying a LangSmith API key + project name (used per-request, not persisted in plaintext — see Security Model). |
| REQ-003 | User can list recent runs from their connected LangSmith project, filterable by status (e.g., failed). |
| REQ-004 | User can alternatively push a run's trace via SDK/webhook using a per-user ingestion token. |
| REQ-005 | User can select a specific run and trigger analysis, supplying their LLM provider key (BYOK) for that request only. |
| REQ-006 | System runs a 2-agent LangGraph workflow: Triage Agent classifies failure type; Remediation Agent retrieves top-K similar resolved cases from Qdrant (scoped to the user) and drafts a proposed fix. |
| REQ-007 | System returns a structured report: failure category, root-cause explanation, supporting evidence (trace excerpts), and a proposed patch/recommendation. |
| REQ-008 | System requires explicit human action (Approve / Reject / Request changes) before a case is considered resolved. |
| REQ-009 | On approval, the run + diagnosis + patch is stored as a "resolved case" and embedded into Qdrant for future retrieval. |
| REQ-010 | User can view history of past analyses and their statuses (Pending, Approved, Rejected). |
| REQ-011 | System must never persist the user's LLM provider key beyond the lifetime of a single analysis request (in-memory only, never written to DB/logs). |
| REQ-012 | System must isolate data per user/workspace (no cross-tenant visibility). |

## 3. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-001 | Security: secrets (LangSmith key, LLM key) never logged or persisted in plaintext; LangSmith key encrypted at rest if stored for reuse (opt-in), LLM key never stored at all. |
| NFR-002 | Reliability: external service failures (LangSmith, Qdrant, LLM provider) fail gracefully with actionable error messages, not silent failure. |
| NFR-003 | Testability: business logic (triage classification, patch construction, similarity ranking glue) is unit-testable independent of live external services via interfaces/mocks. |
| NFR-004 | Performance: analysis of a typical run (<200 steps) completes within a bounded time budget with visible progress state (async job, not a blocking 60s+ HTTP call). |
| NFR-005 | Observability: every analysis run is traceable via structured logs/correlation ID from ingestion → triage → remediation → report. |
| NFR-006 | Deployability: system runs via Docker Compose for local/staging, with a documented path to a single-container-per-service cloud deployment. |
| NFR-007 | Maintainability: LangSmith and SDK/webhook ingestion paths converge on one internal `AgentRun` schema so downstream logic (triage, remediation) is source-agnostic. |

## 4. MVP Scope vs Explicitly Excluded Scope

### 4.1 MVP Scope (in)
- Auth (email/password), LangSmith run listing + fetch, SDK/webhook ingestion, 2-agent LangGraph diagnosis workflow, Qdrant-backed similar-case retrieval, human approval workflow, case history view, BYOK key handling (session-only).

### 4.2 Explicitly Excluded (out of MVP)
- EXC-1: Automated code mutation / auto-PR creation against user repos.
- EXC-2: Multi-agent workflows beyond Triage + Remediation (e.g., no separate "Testing Agent" or "Deployment Agent" yet).
- EXC-3: Cross-customer/global shared case corpus.
- EXC-4: Real-time streaming trace ingestion (MVP is on-demand/batch per run, matching "on-demand platform" in the problem statement).
- EXC-5: Billing/subscription system.
- EXC-6: Support for LLM providers beyond OpenAI/Anthropic.
- EXC-7: Role-based access control beyond single-owner-per-workspace (team seats deferred).
- EXC-8: Kubernetes, message brokers, event streaming, multi-region — no justifying requirement exists yet.

---

## 5. User Journeys

### UJ-1: Connect LangSmith and diagnose a failed run
1. User logs in → Settings → enters LangSmith API key + project name (validated live, not stored in plaintext).
2. User opens "Runs" → sees list of recent runs pulled from LangSmith, filters to `status=error`.
3. User selects a failed run → clicks "Diagnose."
4. Modal requests LLM provider + API key (session-only) → user submits.
5. System shows an async job status ("Triaging… Retrieving similar cases… Drafting fix…").
6. Report appears: category, root cause, evidence (trace excerpt), proposed patch, similar past cases (if any).
7. User clicks Approve, Reject, or Request Changes (free-text note).
8. If Approved → case saved to history and indexed into Qdrant for future retrieval.

### UJ-2: Push a trace via SDK/webhook (no LangSmith)
1. User generates an ingestion token from Settings.
2. User's agent code (or CI) POSTs the run trace JSON to `/api/v1/ingest/run` with the token.
3. Run appears in the same "Runs" list, tagged `source=sdk`.
4. Steps 3–8 of UJ-1 continue identically.

### UJ-3: Review history
1. User opens "History" → sees past analyses with status filters (Pending/Approved/Rejected).
2. User opens a past case to review the original report and decision trail (who approved, when, notes).

---

## 6. Feature / Module Decomposition

| FEAT | Name | Covers REQs |
|---|---|---|
| FEAT-001 | Auth & Workspace | REQ-001, REQ-012 |
| FEAT-002 | LangSmith Integration | REQ-002, REQ-003 |
| FEAT-003 | SDK/Webhook Ingestion | REQ-004 |
| FEAT-004 | Diagnosis Workflow (Triage + Remediation) | REQ-005, REQ-006, REQ-007, REQ-011 |
| FEAT-005 | Human-in-the-Loop Approval | REQ-008, REQ-009 |
| FEAT-006 | Case History & Retrieval | REQ-010 |

Modules map 1:1 to backend service modules (see §7.3) to keep traceability direct.

---

## 7. System Architecture

### 7.1 Architecture Style
A **single deployable backend service (modular monolith)** + **single frontend SPA** + **Postgres** (relational data: users, runs, cases, approvals) + **Qdrant** (vector similarity only). No microservices, no message broker, no Kubernetes — none are justified by current scale/requirements (per Core Engineering Principle). Background job processing (for the async diagnosis workflow) uses a simple in-process async task queue (e.g., FastAPI `BackgroundTasks` + a lightweight job table for status, or a single-process job runner) — not a separate broker like Redis/Celery, because MVP concurrency is low (on-demand, one analysis at a time per user) and a broker is not yet justified. **Decision recorded**: if concurrent analysis volume later requires true background workers across processes, introduce a job queue then (see `/docs/decisions.md`).

### 7.2 High-Level Diagram (textual)
```
[Frontend SPA] --HTTPS--> [Backend API (modular monolith)]
                                |-- Auth module
                                |-- LangSmith client module -----> [LangSmith API]
                                |-- Ingestion module (webhook/SDK)
                                |-- Diagnosis module
                                |      |-- LangGraph: Triage Agent -----> [User's LLM provider, BYOK]
                                |      |-- LangGraph: Remediation Agent -> [User's LLM provider, BYOK]
                                |                              \--------> [Qdrant: similarity search]
                                |-- Approval module
                                |-- History module
                                |
                                |-- Postgres (users, workspaces, runs, cases, approvals, jobs)
                                |-- Qdrant (case embeddings, per-workspace namespace)
```

### 7.3 Backend Modules (maps to FEAT-xxx)
- `auth` (FEAT-001)
- `langsmith_client` (FEAT-002)
- `ingestion` (FEAT-003) — normalizes both LangSmith and SDK input into one `AgentRun` model
- `diagnosis` (FEAT-004) — LangGraph graph definition, Triage node, Remediation node, Qdrant retrieval
- `approval` (FEAT-005)
- `cases` (FEAT-006) — history + Qdrant indexing on approval

### 7.4 Frontend Architecture
React SPA (Vite + TypeScript). Pages: Login/Signup, Settings (LangSmith key, ingestion token), Runs List, Run Detail / Diagnose flow, Report view (with Approve/Reject), History. State: React Query for server state (runs, jobs, cases), no global client-state library needed (no Redux) — server state dominates; local UI state via component state/context only where required (e.g., BYOK key entry form, cleared from memory after submit).

---

## 8. Technology Decisions (with alternatives considered)

| Decision | Requirement Driving It | Alternatives Considered | Trade-offs | Choice |
|---|---|---|---|---|
| Backend language/framework | REQ-006 needs LangGraph (Python-native); NFR-003 testability | Python/FastAPI vs Node/Express vs Python/Django | LangGraph and the LangSmith SDK are Python-first; FastAPI gives async I/O (needed for concurrent external calls to LangSmith/Qdrant/LLM) with less ceremony than Django | **Python 3.12 + FastAPI** |
| Agent orchestration | REQ-006 (2-agent workflow) | Hand-rolled orchestration vs LangGraph vs CrewAI | LangGraph is explicitly named in the problem statement, has first-class support for HITL interrupts (matches REQ-008 directly) | **LangGraph** |
| Relational DB | REQ-001, 009, 010, 012 | Postgres vs MySQL vs SQLite | Postgres: mature, strong JSON column support for storing trace/report payloads, good with SQLAlchemy/Alembic migrations | **PostgreSQL 16** |
| Vector store | REQ-006, REQ-009 (semantic similarity retrieval) | Postgres `pgvector` vs Qdrant vs Pinecone | `pgvector` avoids a second database and is the "simplest option" — evaluated seriously. Qdrant explicitly named in problem statement and provides workspace-scoped collections + filtering out of the box, which reduces custom isolation logic (NFR: security/data isolation). Given the explicit product requirement naming Qdrant and the value of built-in payload filtering for per-workspace isolation (REQ-012), Qdrant is retained as a justified second datastore — this is the one explicit exception to "avoid multiple databases." | **Qdrant** |
| Background job execution | NFR-004 (async, non-blocking) | Celery+Redis vs FastAPI BackgroundTasks + DB-tracked job status vs polling | Celery/Redis is unjustified infra weight at current concurrency; DB-tracked job row + in-process async task satisfies "visible progress, non-blocking" without a broker | **In-process async tasks + `jobs` table in Postgres** |
| Frontend framework | Standard SPA needs, developer-tool UI | React vs Vue vs server-rendered | React has the largest ecosystem overlap with the team's likely familiarity; no SSR/SEO requirement exists (internal tool) | **React + TypeScript + Vite** |
| LLM provider abstraction | REQ-005 BYOK, AMB-4 | LangChain universal chat model interface vs custom thin wrapper | LangChain's chat model classes already provide a uniform interface across OpenAI/Anthropic without building bespoke abstraction | **LangChain chat model interfaces**, key passed per-request, never persisted |
| Auth | REQ-001 | Roll-your-own vs OAuth-only vs email/password + JWT | Email/password + short-lived JWT is simplest for MVP single-tenant workspaces; OAuth deferred (no requirement forces SSO yet) | **Email/password + JWT (access + refresh)** |
| Deployment | NFR-006 | Kubernetes vs single-host Docker Compose vs PaaS | No scale requirement justifies Kubernetes; Docker Compose is simplest reproducible unit for MVP, portable to a PaaS (e.g., Render/Fly/ECS single service) later | **Docker Compose (Postgres, Qdrant, API, Frontend)** |

No microservices, no message broker, no Kubernetes, no Redis are introduced — none justified by current requirements, per the Core Engineering Principle.

---

## 9. Data Model (PostgreSQL)

```
users
  id (uuid, pk)
  email (unique, not null)
  password_hash (not null)
  created_at

workspaces
  id (uuid, pk)
  owner_user_id (fk -> users.id)
  name
  langsmith_project (nullable)
  langsmith_key_encrypted (nullable, encrypted at rest, only if user opts to save it)
  ingestion_token_hash (unique, for SDK/webhook auth)
  created_at

agent_runs
  id (uuid, pk)
  workspace_id (fk -> workspaces.id)
  source (enum: 'langsmith' | 'sdk')
  external_run_id (nullable — LangSmith run id if applicable)
  status (enum: 'success' | 'error' | 'unknown')
  raw_trace (jsonb — normalized AgentRun representation)
  fetched_at

diagnosis_jobs
  id (uuid, pk)
  agent_run_id (fk -> agent_runs.id)
  status (enum: 'pending' | 'running' | 'completed' | 'failed')
  error_message (nullable)
  created_at
  completed_at

diagnosis_reports
  id (uuid, pk)
  diagnosis_job_id (fk -> diagnosis_jobs.id, unique)
  failure_category (text)
  root_cause (text)
  evidence (jsonb — trace excerpts referenced)
  proposed_patch (text)
  similar_case_ids (uuid[] — references resolved_cases.id)
  created_at

approvals
  id (uuid, pk)
  diagnosis_report_id (fk -> diagnosis_reports.id, unique)
  decision (enum: 'approved' | 'rejected' | 'changes_requested')
  reviewer_user_id (fk -> users.id)
  note (nullable text)
  decided_at

resolved_cases
  id (uuid, pk)
  workspace_id (fk -> workspaces.id)
  diagnosis_report_id (fk -> diagnosis_reports.id)
  qdrant_point_id (uuid — pointer into Qdrant collection)
  created_at
```

**Qdrant**: one collection `resolved_cases`, payload includes `workspace_id` (filter field, enforces REQ-012 isolation), `resolved_case_id` (fk back to Postgres row). Embedding = vector of (failure_category + root_cause + trace summary) at approval time.

Indexes: `agent_runs(workspace_id, status)`, `diagnosis_jobs(agent_run_id)`, `resolved_cases(workspace_id)` — driven by the list/filter access patterns in UJ-1/UJ-3, not speculative.

---

## 10. API Contracts (MVP surface)

Base path: `/api/v1`. Auth: `Authorization: Bearer <JWT>` except `/auth/*` and `/ingest/run` (uses ingestion token).

| Method & Path | Purpose | Req body (key fields) | Response (key fields) | REQ |
|---|---|---|---|---|
| `POST /auth/signup` | Create account | email, password | user id, tokens | REQ-001 |
| `POST /auth/login` | Login | email, password | access/refresh tokens | REQ-001 |
| `PUT /workspaces/{id}/langsmith` | Save/validate LangSmith connection | langsmith_key, project | ok/validated | REQ-002 |
| `GET /workspaces/{id}/runs?status=error` | List runs (from LangSmith live or cached) | — | run[] | REQ-003 |
| `POST /ingest/run` | SDK/webhook push a run trace | ingestion_token (header), trace JSON | agent_run id | REQ-004 |
| `POST /runs/{id}/diagnose` | Start diagnosis job | llm_provider, llm_api_key (never persisted) | job id, status=pending | REQ-005, REQ-011 |
| `GET /jobs/{id}` | Poll job status | — | status, report_id (when completed) | REQ-006, NFR-004 |
| `GET /reports/{id}` | Get diagnosis report | — | category, root_cause, evidence, proposed_patch, similar_cases[] | REQ-007 |
| `POST /reports/{id}/approval` | Approve/reject/request changes | decision, note | approval record | REQ-008 |
| `GET /workspaces/{id}/cases?status=` | History list | — | case summaries | REQ-010 |

Error model: standard `{ "error": { "code": "...", "message": "..." } }`, HTTP status codes 400 (validation), 401/403 (auth), 404, 409 (duplicate ingestion), 422 (external service, e.g. LangSmith unreachable), 500.

---

## 11. Security Model

- **BYOK key handling (REQ-011, NFR-001)**: `llm_api_key` accepted only in the `diagnose` request body over TLS, held in memory only for the duration of the LangGraph run, never written to logs, DB, or error messages. Structured logging must scrub any field matching key-like patterns as defense in depth.
- **LangSmith key**: if the user opts to save it (for repeated run-listing), it is encrypted at rest (e.g., AES-GCM with a server-held KMS/env-provided key) — never stored in plaintext, never returned in API responses after initial save.
- **AuthN**: JWT access (short-lived, ~15 min) + refresh token (rotated, stored hashed).
- **AuthZ**: every resource query scoped by `workspace_id` derived from the authenticated user's session — no client-supplied workspace id trusted without ownership check (mitigates IDOR).
- **Ingestion token**: random high-entropy token, stored hashed, scoped to one workspace, rate-limited per token.
- **Input validation**: all request bodies validated via Pydantic schemas; trace JSON size-capped (reject oversized payloads) to avoid resource exhaustion on ingestion.
- **Injection risks**: no raw SQL string concatenation — SQLAlchemy ORM/parameterized queries throughout.
- **CORS**: restricted to the deployed frontend origin(s) only.
- **CSRF**: not applicable in the classic sense (JWT bearer token in Authorization header, not cookies) — if refresh tokens are cookie-based, mark `HttpOnly`, `Secure`, `SameSite=Strict`.
- **XSS**: React auto-escapes by default; proposed-patch/evidence text rendered as text, never `dangerouslySetInnerHTML`.
- **Rate limiting**: applied to `/auth/login` (brute-force) and `/ingest/run` (abuse) and `/runs/{id}/diagnose` (cost control, since each call spends the user's own LLM quota but still hits our infra).
- **Dependency vulnerabilities**: CI runs `pip-audit` / `npm audit` as part of the security gate before merge.
- **Data isolation (REQ-012)**: enforced at both the Postgres query layer (workspace_id filter) and the Qdrant payload filter layer (defense in depth).

---

## 12. Testing Strategy

| Level | Focus | Examples |
|---|---|---|
| Unit | Triage classification logic, patch-drafting prompt assembly, AgentRun normalization (LangSmith→internal, SDK→internal), key-scrubbing log filter | Given a known trace pattern (e.g., repeated identical tool call), Triage classifies as "infinite loop" |
| Integration | API endpoints against a test Postgres + mocked Qdrant + mocked LLM provider; ingestion webhook auth; workspace isolation (attempt cross-workspace access → 403) | `POST /ingest/run` with invalid token → 401; `GET /workspaces/{other}/runs` as non-owner → 403 |
| E2E | UJ-1 full happy path (connect → list → diagnose → approve); UJ-2 SDK ingestion path | Playwright/Cypress against a docker-compose test stack with a mocked LLM provider |

Also tested per the required categories: invalid input (bad trace JSON), missing data (LangSmith key not set → clear error not crash), duplicate data (same `external_run_id` ingested twice → idempotent), unauthorized/forbidden access (see above), boundary conditions (empty trace, max-size trace), external service failures (LangSmith 500, Qdrant down, LLM provider timeout → job marked `failed` with message, not silently hung), concurrency (two diagnosis requests on the same run — second is rejected or queued, not double-processed).

No coverage-padding tests will be added; each test maps to a REQ/NFR above.

---

## 13. Deployment Strategy

- **Local/staging**: `docker-compose.yml` with services `api`, `frontend`, `postgres`, `qdrant`. `.env` file (git-ignored) for secrets/config; `.env.example` committed.
- **Migrations**: Alembic, run as an explicit step (`alembic upgrade head`) in the deploy pipeline, never implicit at app boot in production.
- **Production path**: same containers deployed as individual services on a PaaS (e.g., Fly.io/Render/ECS) or a single VM via Compose for early-stage — no Kubernetes until real multi-instance scaling is required.
- **CI**: lint (ruff/eslint) → type-check (mypy/tsc) → unit+integration tests → build Docker images → (staging) run E2E → security checks (pip-audit/npm audit).
- **Secrets in deployment**: environment variables / platform secret manager — never committed.

## 14. Observability Strategy

- Structured JSON logs with a `correlation_id` per diagnosis job, propagated through ingestion → triage → remediation → report, satisfying NFR-005.
- Key metrics (even if just logged initially, dashboard later if justified): diagnosis job success/failure rate, average diagnosis latency, external service error rates (LangSmith/Qdrant/LLM).
- No dedicated observability stack (no Prometheus/Grafana) introduced in MVP — not yet justified by scale; structured logs are sufficient for a single-service MVP.

---

## 15. Development Roadmap (Vertical Slices)

Ordered by dependency, architectural risk, core value, and technical uncertainty.

### SLICE-001 — Auth & Workspace Bootstrap
- **Objective**: A user can sign up, log in, and has a workspace created automatically.
- **Requirements covered**: REQ-001, REQ-012
- **Dependencies**: none (foundation)
- **DB**: `users`, `workspaces`
- **API**: `POST /auth/signup`, `POST /auth/login`
- **Frontend**: Signup/Login pages, auth token storage, protected route wrapper
- **Tests**: unit (password hashing, JWT issuance), integration (signup→login flow, duplicate email rejected, wrong password rejected)
- **Security**: password hashing (bcrypt/argon2), JWT expiry, rate-limit login
- **Acceptance criteria**: new user can sign up, log in, and land on an authenticated Runs page showing "no runs yet."

### SLICE-002 — LangSmith Connection & Run Listing
- **Objective**: User connects LangSmith and sees their failed runs.
- **Requirements covered**: REQ-002, REQ-003
- **Dependencies**: SLICE-001
- **DB**: `workspaces.langsmith_project`, `langsmith_key_encrypted`; `agent_runs` (cache of fetched runs)
- **API**: `PUT /workspaces/{id}/langsmith`, `GET /workspaces/{id}/runs`
- **Frontend**: Settings page (LangSmith form), Runs List page with status filter
- **Tests**: integration with mocked LangSmith client (valid key, invalid key, LangSmith unreachable), unit (encryption/decryption round-trip)
- **Security**: encryption at rest for saved key, key never returned in GET responses
- **Acceptance criteria**: invalid LangSmith key shows a clear validation error; valid key lists real runs filterable by `error` status.

### SLICE-003 — SDK/Webhook Ingestion
- **Objective**: A run trace can be pushed in without LangSmith.
- **Requirements covered**: REQ-004
- **Dependencies**: SLICE-001
- **DB**: `workspaces.ingestion_token_hash`, `agent_runs`
- **API**: `POST /ingest/run`
- **Frontend**: Settings page — "generate ingestion token"
- **Tests**: integration (valid token accepted, invalid/rotated token rejected, duplicate `external_run_id` idempotent, oversized payload rejected)
- **Security**: token hashing, per-token rate limit, payload size cap
- **Acceptance criteria**: a curl/SDK POST with a valid token produces a run visible in the Runs list tagged `source=sdk`.

### SLICE-004 — Diagnosis Workflow (Triage + Remediation, core value slice)
- **Objective**: Selecting a run and providing an LLM key produces a structured diagnosis report.
- **Requirements covered**: REQ-005, REQ-006, REQ-007, REQ-011
- **Dependencies**: SLICE-002 or SLICE-003 (needs at least one run present)
- **DB**: `diagnosis_jobs`, `diagnosis_reports`
- **API**: `POST /runs/{id}/diagnose`, `GET /jobs/{id}`, `GET /reports/{id}`
- **Frontend**: "Diagnose" button + BYOK key modal, job progress view, report view
- **Tests**: unit (Triage classification on fixture traces for each known failure type: schema drift, context exhaustion, tool failure, infinite loop, silent state loss), integration (full job lifecycle with mocked LLM + mocked/empty Qdrant, LLM provider timeout → job `failed` with message, key never appears in logs — asserted explicitly), concurrency (second concurrent diagnose call on same run handled without double-processing)
- **Security**: key-in-memory-only path verified by log-scrub test; per-user rate limit on diagnose endpoint
- **Acceptance criteria**: given a fixture failed trace, the report shows a plausible failure category, root cause referencing actual trace evidence, and a proposed patch; job never blocks the HTTP request thread for its full duration (async).

### SLICE-005 — Human-in-the-Loop Approval + Case Storage
- **Objective**: User can approve/reject a report; approved cases feed Qdrant for future retrieval.
- **Requirements covered**: REQ-008, REQ-009
- **Dependencies**: SLICE-004
- **DB**: `approvals`, `resolved_cases`
- **API**: `POST /reports/{id}/approval`
- **Frontend**: Approve/Reject/Request-changes controls on report view
- **Tests**: integration (approve → case appears in `resolved_cases` and is embedded into Qdrant with correct `workspace_id` payload; reject → no Qdrant write; double-approval rejected/idempotent)
- **Security**: only the report's workspace owner (or authorized reviewer) may approve — authorization check test included
- **Acceptance criteria**: approving a report creates exactly one `resolved_cases` row and one Qdrant point scoped to the workspace.

### SLICE-006 — Similar-Case Retrieval in Remediation
- **Objective**: Remediation Agent actually queries Qdrant for similar past cases and includes them in the report.
- **Requirements covered**: REQ-006 (similarity portion), REQ-012 (isolation)
- **Dependencies**: SLICE-004, SLICE-005 (needs at least one resolved case to retrieve against)
- **DB**: read from `resolved_cases`/Qdrant
- **API**: extends `GET /reports/{id}` response with `similar_cases[]`
- **Frontend**: "Similar past cases" section on report view
- **Tests**: integration (workspace A's resolved case never returned for workspace B's diagnosis — explicit cross-tenant isolation test), unit (top-K ranking logic)
- **Security**: Qdrant query always includes `workspace_id` filter — tested explicitly as a security-critical isolation boundary
- **Acceptance criteria**: after approving one case, a subsequent similar failure in the same workspace surfaces it as a "similar case"; it never surfaces for a different workspace.

### SLICE-007 — History View
- **Objective**: User can browse past analyses and their decisions.
- **Requirements covered**: REQ-010
- **Dependencies**: SLICE-005
- **API**: `GET /workspaces/{id}/cases?status=`
- **Frontend**: History page with status filter
- **Tests**: integration (filter correctness, pagination boundary)
- **Acceptance criteria**: history page lists all past reports with correct status and reviewer/decision metadata.

### SLICE-008 — Hardening & Production Readiness
- **Objective**: Cross-cutting security/observability/deployment gates closed before calling MVP done.
- **Requirements covered**: NFR-001..007 (verification, not new features)
- **Dependencies**: all prior slices
- **Work**: rate limiting audit, dependency vuln scan, log-scrubbing audit, Docker Compose full-stack smoke test, structured logging correlation IDs verified end-to-end, `.env.example` completeness check
- **Acceptance criteria**: full test suite passes, `docker compose up` brings up a working stack against which UJ-1 and UJ-2 can be manually verified end-to-end.

---

## 16. Decisions Log Summary (also to be kept in `/docs/decisions.md`)
- Qdrant retained as the one justified second datastore (semantic similarity + built-in per-workspace filtering).
- No message broker/Celery — in-process async + DB-tracked job status sufficient at MVP concurrency.
- No Kubernetes — Docker Compose sufficient; revisit only if real horizontal-scaling need appears.
- "Applying" a fix in MVP = human approval + case storage, not automated code mutation (AMB-1).
- LangSmith key persistence is opt-in and encrypted; LLM (BYOK) key is never persisted under any circumstance.

---

## 17. Open Questions for the User (per Autonomy Rule — genuine ambiguities)
1. Confirm AMB-1: is it acceptable that MVP does **not** automatically apply patches to user code/repos, only records the approved recommendation? (Assumed **yes** for MVP per problem statement wording; flag if actual expectation is auto-PR creation — that would be a materially larger, riskier scope.)
2. Confirm AMB-3: is a per-user/workspace-only case corpus acceptable for MVP, or is a shared cross-customer knowledge base a hard requirement from day one? (Assumed workspace-scoped only, for privacy.)
3. Confirm provider scope (AMB-4): is OpenAI + Anthropic sufficient for MVP BYOK, or is a specific third provider (e.g., local/self-hosted models) required immediately?

Implementation (MODE 2) will proceed slice-by-slice starting at SLICE-001 once this document is confirmed or amended.
