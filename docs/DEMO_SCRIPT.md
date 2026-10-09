# Six-minute panel walkthrough

1. **Opening, 30 seconds.** Explain the problem: agents need accountable identities, purpose-bound access, constrained delegation and traceable decisions. State that this is an offline governance prototype with deterministic agents and simulated identities.
2. **Allowed workflow, 60 seconds.** As Employee, run Approved workflow. Show the child delegation, masked case response and tool execution delta of two.
3. **Denied requests, 60 seconds.** Run Unapproved destination and Out-of-scope record. Show zero tool executions and the reasons in the timeline. No external destination is contacted.
4. **Agent-specific controls, 60 seconds.** Run Privilege expansion and Direct-tool bypass. Explain that one demonstrates narrowed delegation and the other a credential check at a separate local tool endpoint. Neither establishes network isolation.
5. **Human approval, 90 seconds.** Run Approval-gated update. Show no mutation before approval. Switch to Reviewer, approve the exact case/status/version, and show a single mutation. Explain request binding, expiry, idempotency and independent review.
6. **Emergency control, 45 seconds.** Switch to Operator, run Suspend and stop descendants and show the denied child call. Reactivate the coordinator for the next demo. Old grants remain revoked.
7. **Roadmap, 15 seconds.** Explain that SSO, workload identity, approved cloud networking, real MCP/model integrations and immutable evidence are the next sandbox steps.

## Likely panel questions

**Where is the AI?** The demo uses repeatable scripted agents to prove governance. A live model can later propose actions through the same authorization path. Model randomness is deliberately separated from control validation.

**Why no cloud today?** The deadline is today and destination network permissions are uncertain. The archive runs without outbound services; cloud adapters and enterprise identity need approved infrastructure.

**Is this an MCP gateway?** Not yet. It is a governed local HTTP tool adapter demonstrating the contract. A tested MCP adapter is a future integration.

**Is direct access impossible?** The tool rejects missing gateway credentials. The local network remains reachable and the same-user machine is not an isolation boundary. Production requires network restrictions and workload identity.

**Can a user choose Reviewer?** Yes. The selector is explicitly a persona simulator. Enterprise authentication and real separation of duties are future work.

**What survives restart?** Registry state, case state, approvals and evidence persist. Old grants are revoked, pending approvals expire and interrupted execution is marked unknown.

**What if approvals expire on stage?** Start a new approval scenario and approve promptly. Do not extend an expired grant silently.
