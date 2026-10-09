# Agent Governance - offline banking demo

Version 0.2 | Same-day demonstration | Synthetic data only

This project demonstrates governance of scripted agents: verified demo credentials, purpose-scoped temporary grants, constrained delegation, masked reads, exact-request approval, suspension, a gateway credential check at a separate tool service, and an audit timeline.

## Start here

1. Extract the project into a folder you may write to.
2. Use an organization-approved **Python 3.10 or later** with SQLite support.
3. On Windows, double-click **start_demo.cmd**. Alternatively, open a terminal in this folder and run `python app.py`.
4. Open **http://127.0.0.1:8765** in an approved browser. Keep the terminal open.
5. Begin as **Employee** and click **Approved workflow**. Use the demo script in `docs/DEMO_SCRIPT.md`.

There is **no pip install, npm install, external model call, account registration, CDN, internet connection, Docker requirement or administrator requirement** in the normal demo path. An approved Python installation, browser, writable folder, subprocess execution and local loopback sockets are still required. If those are blocked by corporate policy, use the documented presentation fallback and request the appropriate approval; do not bypass endpoint controls.

## Files to read

- `docs/HANDBOOK.md` and `docs/03_Project_Handbook.pdf`: current implemented architecture, source map, learning guide, operations and future cloud path.
- `docs/IMPLEMENTATION_PLAN.md` and `docs/02_Implementation_Plan.pdf`: revised same-day scope and next stages.
- `docs/DEMO_SCRIPT.md`: six-minute presentation walkthrough.
- `docs/TEST_REPORT.md`: actual validation results and their limits.
- `docs/01_Problem_Statement.pdf`: original requirements synthesis.
- `docs/archive/`: original design baseline, retained as historical proposals.

## Run tests and check the machine

```text
python app.py --check
python -m unittest discover -s tests -v
```

On Windows, `py -3` can replace `python`. Double-click `run_tests.cmd` to run the tests. They use temporary databases and a separate local tool process. The app never needs NumPy, Pandas or Scikit-learn.

## Start clean without deleting evidence

Stop the server with Ctrl+C. Start with a new data directory:

```text
python app.py --data-dir data/demo-session-2
```

Use `--port 8766` if the default port is already occupied, then open the corresponding local address. Normal state persists under `data/`. Restarting revokes old grants, expires pending approvals, and marks interrupted executions unknown. It preserves suspended agent states and case history. Operator reactivation allows fresh grants; it does not revive old grants.

## What this is not

This is a **local governance prototype**, not an enterprise security product. Agents are deterministic scripts, not LLM-driven agents. Human roles are selectable demo personas, not authenticated employees. Network isolation, enterprise SSO, cloud federation, real MCP integration, live model access, immutable audit storage and production deployment are not implemented. The standard-library HTTP server must not be exposed as a production service. No claim is made that this software is approved by Infosys.

## Sharing the package

`dist/AgentGovernanceDemo.zip` contains source, static web assets, documentation and tests. It excludes databases, temporary files, caches and credentials. It does not bundle a Python interpreter; obtain that through your organization's approved route. Transfer the archive only through approved channels. Read the handbook's portability section before presenting on another machine.
