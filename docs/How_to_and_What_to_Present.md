# How to and What to Present

Version 0.2 | Guided rehearsal | 09 October 2026

## How to and What to Present

A step-by-step companion for understanding, rehearsing and presenting the Agent Governance demo.

### Read one page. Run one step. Pause.

This guide is designed for learning together, not rushing through a script. For each step, understand its purpose, perform the action, verify the result and explain it in your own words. Discuss the pause question before moving on.

### The correct description

An offline governance prototype with scripted agents and synthetic banking data. The local policy checks, separate tool service, database updates and evidence records actually execute. Human identities are simulated.

### Find your place

| Pages | Topic |
|---|---|
| 2-3 | Introduce the problem, understand the dashboard and run approved work. |
| 4-6 | Demonstrate denied access, constrained delegation and the tool credential boundary. |
| 7-9 | Demonstrate exact-request approval, suspension and the audit trail. |
| 10-11 | Optional identity/expiry tests, architecture and source-file map. |
| 12-14 | Panel questions, setup/recovery and a rehearsal checklist. |

### How this relates to the other documents

The problem statement explains why the framework is needed. The current implementation plan explains the same-day scope and next stages. The handbook explains the actual code. This guide explains how to show and defend that work in a presentation.

Status: version 0.2, based on the current local demo and its recorded validation. Twenty-five automated tests passed locally. The browser walkthrough confirmed the approved workflow and a reviewer-approved case update. The destination enterprise environment has not been tested.

Prepared 09 October 2026. Source: the project implementation, current handbook, demo script and recorded local test results. No software changes are made by this guide.

## 1. Introduce the problem and dashboard

Begin with the purpose of the project before discussing technology.

### What to show

Show the overview and agent registry. Identify the Case coordinator, Knowledge agent and Case update agent. Each record has an owner label, approved purpose, permitted actions and active/suspended state.

### What to say

Enterprises are introducing agents that can use tools, access data and delegate work. We need a consistent way to assign ownership, limit each task's authority, require approval for sensitive actions and explain what happened. This prototype demonstrates that governance loop using a synthetic banking case.

| Dashboard item | What it means |
|---|---|
| Registered agents | The three seeded agent definitions. This is not automatic enterprise discovery. |
| Blocked attempts | Recorded policy denials and direct-tool credential rejections. |
| Tool executions | Successful operations recorded by the separate tool service. |
| Case status / version | The current synthetic case state and its record version. |
| Demo persona | Employee, Reviewer, Operator or Auditor. This is a role simulator, not real login. |

### Likely question: what does ownership provide?

It identifies the team accountable for an agent's intended use and configuration. Owner labels are seeded for this demo; they are not synchronized with an employee directory.

### Pause and explain

In one sentence, explain the business problem without naming Python, a cloud provider or an AI model. Then identify the counters and persona selector on screen.

## 2. Show an approved workflow

Prove that legitimate work can proceed under governance.

### What to click

Select Employee. Run Approved workflow. Read the Latest scenario result before continuing.

### What happens inside

The coordinator receives a five-minute task grant for the selected synthetic case. It delegates a narrower knowledge-read task to the Knowledge agent. The child calls the knowledge tool. The coordinator then reads the case through the gateway, which filters the response before returning it.

| Check | Expected result |
|---|---|
| Delegation | An allowed child task is created with knowledge-read permission. |
| Knowledge lookup | The approved article/guidance is returned. |
| Case response | Account number is shown as [MASKED]; the raw customer field is absent. |
| Tool execution delta | Two: one knowledge read and one case read. Delegation itself is not a tool call. |
| Timeline | Task, delegation, policy decisions, tool actions and masking events are present. |

### What to say

Governance does not mean blocking every action. This request fits the approved purpose and scope, so it proceeds. The gateway constrains what is returned and records the decisions.

### Likely question: where is the AI?

There is no live language model in this version. Scripted agents make the control demonstration repeatable and avoid external calls. A future model would propose actions through the same authorization boundary.

### Pause and explain

Find the masked field and the execution delta of two. Explain why three displayed steps do not mean three tool executions.

## 3. Show requests being denied

Demonstrate resource and destination restrictions as separate controls.

### What to click

As Employee, run Unapproved destination. Inspect its reason and execution delta. Then run Out-of-scope record and inspect that result separately.

| Scenario | Expected evidence |
|---|---|
| Unapproved destination | The gateway denies the destination label. Tool execution delta is zero. No external endpoint is contacted. |
| Out-of-scope record | The request targets a case outside the task grant. Tool execution delta is zero. |

### What to say

Access depends on the concrete task, action, resource and destination. An agent's broad business purpose does not authorize every customer record or permission to send data anywhere.

### How the code makes this decision

The gateway compares the requested case with the grant's case scope and checks that the destination is internal. Invalid authority is rejected before tool dispatch. The response includes a specific denial reason, and the event timeline records it.

### Likely question: is the external network blocked?

This scenario tests a local destination rule. It does not attempt an external connection and does not establish a firewall or network-isolation guarantee. Production egress enforcement is a separate future requirement.

### If your counters are not zero

The total counter includes earlier runs. Use the latest scenario's execution delta to identify what changed during this attempt. A denied scenario should add no successful tool executions.

### Pause and explain

Explain why the two requests are rejected for different reasons. Show evidence that neither request caused a tool execution.

## 4. Show constrained delegation

Passing work to another agent must not create new authority.

### What to click

Run Privilege expansion.

### Expected result

The request tries to give the Knowledge agent case-writing authority. Delegation is denied because that child is eligible only for knowledge reads. The tool execution delta remains zero.

### What to say

A child task must fit both its parent's authority and the child agent's own eligibility. An agent cannot avoid restrictions simply by asking another agent to perform an operation.

| Concept | Plain-language meaning |
|---|---|
| Identity | Which agent is calling? |
| Agent eligibility | Which actions may this registered agent be considered for? |
| Task grant | What may this agent do for this particular task, record and time window? |
| Delegation | A child gets its own narrower grant, linked to its parent. |

### Other implemented delegation checks

The engine checks that agents are active, rejects cycles, limits delegation to two edges and keeps child expiry within the parent deadline. Each call checks the grant ancestry so a revoked parent also prevents descendant calls.

### Likely question: does the child reuse the parent token?

No. The child uses its own demo agent identity and a separately recorded grant. This is a local implementation of the authority structure; it is not a demonstration of enterprise token exchange or cross-cloud federation.

### Pause and explain

Use the Knowledge agent as an example to distinguish identity, eligibility and task-specific authority.

## 5. Show the direct-tool check

Demonstrate a real credential check at the separate local tool service.

### What to click

Run Direct-tool bypass.

### Expected result

The scenario sends a real loopback HTTP request to the tool service without its gateway credential. The service rejects it before tool execution. The result shows a credential-required reason and an execution delta of zero.

### What to say

The tool service checks the caller credential itself. This is not just a red status displayed by the dashboard: the separate service rejects the unauthenticated request before it runs the operation.

| Proved here | Not proved here |
|---|---|
| The endpoint rejects a missing gateway credential. | The agent is unable to reach that endpoint over the network. |
| The tool execution count does not increase. | A hostile program under the same local user cannot obtain credentials. |
| The synthetic service executes in a separate process. | Production workload identity, process isolation or encrypted transport. |

### Likely question: what changes for production?

Use isolated workloads, verified workload identities, destination-specific authorization, protected secrets, TLS and approved network restrictions. A gateway SDK alone is not an isolation boundary.

### Why this approach today

It gives the panel a repeatable tool-side check without installing system services, changing firewall policy or requiring a cloud account. The shared local machine remains an explicit limitation.

### Pause and explain

Say exactly what the bypass test proves, then name one protection that still needs an enterprise deployment.

## 6. Show approval before a case update

A reviewer approves the exact request; current authority is checked again before execution.

### What to click

As Employee, run Approval-gated update. Inspect the queued case, proposed status and expected record version. Switch to Reviewer and select Approve exact change.

| Before approval | After approval |
|---|---|
| The case update is pending. No tool write has occurred. | One tool write occurs and the approval becomes succeeded. |
| The queue shows the exact target, status and version. | The case version increases. The status is Under review. |

### What to say

Approval is bound to the agent, task grant, exact request and policy version. Before executing, the system checks that the request is unchanged and its authority is still valid. Approval does not override revoked or expired permissions.

### What prevents duplicate or incorrect writes?

The gateway consumes approval once under a local lock. The tool uses an idempotency key so the same execution is not repeated, and checks the expected case version so a stale request cannot overwrite newer state. Automated tests cover altered requests, reused approvals, concurrent approvals and stale versions.

### Timing and repeated rehearsals

Task grants last five minutes. Approval records last ten minutes but cannot extend the task grant. Approve promptly; otherwise create a fresh request. If the case is already Under review, its status label may not visibly change, but its version and the execution count should increase once.

### Likely question: are these real separate employees?

No. Reviewer and Employee are selectable demo personas. The role-dependent logic is implemented, but real authenticated separation between people needs enterprise login.

### Pause and explain

Explain why approval is more than a yes/no button. Identify two reasons an approved request may still fail to execute.

## 7. Show suspension and revocation

Stop subsequent protected actions without claiming that completed work can be undone.

### What to click

Switch to Operator. Run Suspend and stop descendants. Inspect the coordinator's state and the denied child call.

### Expected result

The scenario creates a child task, suspends the coordinator and then attempts a child tool call. The parent grant is revoked, so the child's next protected call is denied. The denied call adds no tool execution.

### What to say

Suspension is an operational control for stopping future authorized dispatch. Each descendant request checks its parent-grant chain, so delegating a task does not hide it from revocation.

### Return the demo to a usable state

As Operator, reactivate the coordinator in the registry. Start a fresh scenario afterward. Reactivation permits new grants; it does not restore previously revoked grants.

| Term | Meaning |
|---|---|
| Revocation | Withdraw authority for subsequent actions. |
| Cancellation | Ask an already-running operation to stop, where supported. |
| Rollback / remediation | Undo or correct an already-completed side effect, where possible. |

### Likely question: does the kill switch reverse everything?

No. This implementation rejects new dispatch through the governed path. An external action that has already completed cannot be reversed merely by suspending an agent. In-flight or uncertain actions need tool-specific cancellation and reconciliation.

### Pause and explain

Show the suspended state and denial, then reactivate the coordinator. Explain why an old grant still cannot be reused.

## 8. Explain the evidence timeline

Use the record of observable decisions and actions to make the demonstration explainable.

### What to show

Inspect Decision timeline. Filter by an agent, event type, reason or run. Export recent evidence if you need a portable record of the demonstration.

| Event family | What it tells you |
|---|---|
| Task / delegation | Which agent received authority and how parent and child tasks connect. |
| Policy decision | Whether the request was allowed, denied or required approval, and why. |
| Tool dispatch / completion | Whether an operation was sent to the tool and what outcome was observed. |
| Data masking | Which restricted field names were filtered from the response. |
| Approval / suspension | Which demonstration control was applied before later actions. |

### What to say

We can reconstruct the observable action path: the task, delegated authority, decision, approval if needed, tool action and result. We do not need to expose private model reasoning or raw credentials to explain an access decision.

### Limits of the current evidence store

The dashboard and export contain the most recent 150 events. The local SQLite database retains full history. It is durable local evidence, but not an immutable or independently controlled audit archive. A local user with filesystem access can modify it. Production retention and audit access controls are future work.

### Likely question: where is sensitive data stored?

All case data is synthetic. Ordinary event details omit raw account values and credentials. The synthetic tool database does contain its synthetic source records. This does not establish a general privacy or regulatory compliance guarantee.

### Pause and explain

Trace one allowed tool call and one denied request. Point to the decision reason and the presence or absence of tool execution.

## 9. Optional identity and expiry tests

Use these when the panel asks how identity and temporary authority are checked.

### Unknown identity

As Employee, run Unknown identity. The scenario presents an invalid demo agent credential to the gateway. Expect an identity denial and zero additional tool executions. Identity is resolved from a credential mapping rather than an agent name supplied in the request.

### Expired task grant

Run Expired task grant. The scenario creates a task grant, deliberately expires it, and attempts an otherwise valid case read. Expect an expiry denial and zero additional tool executions.

### What to say

A valid-looking action is not enough. The caller must be recognized and its task authority must still be active. Temporary grants reduce how long permission remains usable; explicit revocation handles changes before expiry.

### Likely question: are these production identities?

No. Opaque agent tokens are generated locally at application startup. Enterprise identity federation, workload attestation, key management and real requester entitlements are not implemented. The tests demonstrate local credential and grant handling.

### What happens after a restart?

Agent and case state persist. Old task grants are revoked, pending approvals expire and interrupted executing approvals become unknown. Fresh authority is needed before new work runs. A previously suspended agent remains suspended until an Operator reactivates it.

### Pause and explain

Distinguish an unrecognized caller, an expired grant and a revoked grant. All can prevent a call, but they describe different conditions.

## 10. Explain the architecture and files

Describe the execution path first, then use the source map when technical questions arise.

### Execution path

Browser -> local application -> governance engine -> credential-protected local tool process -> synthetic case database. The response returns through gateway filtering. Control state and audit events are stored separately from tool records.

| File / area | Responsibility |
|---|---|
| app.py | Browser server, sessions, host/origin checks, CSRF, routes and role-dependent operations. |
| governance.py | Agent tokens, grants, delegation, request policy, approval binding, masking, suspension and event records. |
| tool_server.py | Separate local service, gateway credential check, synthetic reads/writes and execution idempotency. |
| web/index.html | Dashboard structure and sections. |
| web/style.css | Appearance and responsive layout. |
| web/app.js | Scenario controls, API calls, results, approvals and timeline rendering. |
| tests/test_governance.py | Twenty-five automated local tests covering core and HTTP behavior. |
| start_demo.cmd / run_tests.cmd | Windows launchers for the application and tests. |
| docs / data | Documentation / runtime databases. Keep runtime data out of a clean transfer package. |

### Why this stack?

Python standard-library services, SQLite and local JavaScript avoid a package-download or frontend-build requirement on the destination computer. No NumPy, Pandas or Scikit-learn is needed. The built-in server is a local-demo choice, not a production web stack.

### Pause and learn

Read scenario, invoke, validate and execute in governance.py. Match one function to each part of the execution path before studying the whole repository.

## 11. Answer likely panel questions

Use precise answers that separate implemented controls from the enterprise roadmap.

| Question | Answer |
|---|---|
| Is this an AI-agent platform? | It is a governance prototype around agent actions. Today the agents are scripted; a real agent framework can later use the same controlled tool path. |
| Is it an MCP gateway? | Not yet. The demo uses a synthetic HTTP tool adapter. A tested MCP integration is a future step. |
| Why no cloud or live model? | The deadline is immediate and enterprise network permissions are uncertain. The demo avoids external calls and uses repeatable synthetic data. |
| Can someone choose Reviewer? | Yes. Human roles are explicitly simulated. Real login and authenticated separation of duties remain future integrations. |
| Is all sensitive data protected? | The demo filters specific structured fields and rejects unapproved destinations. It does not implement comprehensive unstructured-data detection. |
| Are audit logs immutable? | No. They are local SQLite records. Independently protected storage and retention are future requirements. |
| Does it scale to thousands of agents? | That has not been measured. A small local demonstration is not a production capacity benchmark. |
| What has actually been tested? | Twenty-five automated tests passed locally. Browser checks confirmed approved reads and a reviewer-approved update. No enterprise deployment or penetration test is claimed. |
| What is needed for production? | Approved hosting, enterprise identity, isolated workloads, managed secrets, network enforcement, real adapters, production storage, audit controls and operational ownership. |

### Pause and explain

Choose two questions and answer each in your own words. If a capability is only planned, name it as planned instead of presenting it as delivered.

## 12. Prepare and recover the demo

Rehearse with an approved local runtime and preserve evidence when starting fresh.

### Before presenting

Use approved Python 3.10 or later with SQLite, a modern browser, a writable project directory, permission for local loopback sockets and permission to start a child Python process. No external network call or third-party runtime package is required. The destination Infosys environment has not been validated.

### Start and check

Double-click start_demo.cmd and keep its terminal open. The default browser address is http://127.0.0.1:8765. From a terminal in the project folder, python app.py --check checks the local prerequisites. python -m unittest discover -s tests -v runs the automated tests.

| Situation | Response |
|---|---|
| Port already in use | Start with python app.py --port 8766, then open the corresponding local address. |
| Need a clean rehearsal | Stop the app and use python app.py --data-dir data/rehearsal-2. A new directory preserves prior evidence. |
| Coordinator is suspended | Select Operator, reactivate it, then start a fresh scenario. |
| Approval / grant expired | Create a new approval scenario and approve promptly. Do not silently extend old authority. |
| Tool outcome is unknown | Do not blindly repeat the write. Inspect the tool execution record before reconciliation. |
| Local execution is prohibited | Use the guide and recorded evidence, and request an approved environment. Do not bypass enterprise controls. |

### Sharing the project

Transfer source, local web assets, tests and current documentation through approved channels. Exclude runtime databases, caches and credentials. The guide does not certify that a final transfer ZIP has been produced or that the project has run inside Infosys.

### Pause and verify

Confirm the app starts on the actual presentation machine. Verify that you can run the approved workflow before the panel session begins.

## 13. Rehearsal checklist and closing

Learn slowly first. Use the shorter sequence only when you are ready to present.

| Presentation order | Suggested time |
|---|---|
| Problem and accountable agent registry | 45 seconds |
| Approved delegation and masked read | 60 seconds |
| Destination and record-scope denials | 60 seconds |
| Delegation expansion and direct-tool check | 60 seconds |
| Exact-request human approval | 90 seconds |
| Suspension and descendant denial | 45 seconds |
| Evidence and next steps | 60 seconds |

### Questions to answer during our rehearsal

1. What business problem are we solving?
2. How does an identity differ from a task grant?
3. Why does the approved workflow execute two tools?
4. What exactly does the bypass test prove?
5. Why can approval still fail at execution time?
6. Why do revoked grants stay invalid after reactivation?

### What to say when closing

This prototype demonstrates a repeatable governance loop around agent actions: permitted work proceeds, out-of-scope requests are denied, sensitive changes require review and the results are traceable. The next phase replaces simulated identities and synthetic integrations with approved enterprise services while preserving the tested control behavior.

### Keep the documents aligned

Use the current handbook for implementation details and the implementation plan for future stages. Update this guide whenever scenario labels, expected counts, grant lifetimes, role behavior or approval semantics change. Retain the distinction between implemented, tested and planned capabilities.

### Final checkpoint

You should be able to demonstrate each claim and explain one limitation without assistance. Pause on any unclear step; understanding matters more than completing the script quickly.
