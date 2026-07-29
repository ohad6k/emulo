# PREFLIGHT: Agent-run checklist

## Authentication

- Confirm the model/provider session is authenticated.
- Run one harmless model turn before the measured task.

## Repository

- Record the commit hash.
- Confirm the working tree is clean.
- Create a disposable file and remove it.

## Permissions

- Confirm the agent can read the target files.
- Confirm the agent can write inside the intended workspace.
- Record sandbox and approval modes.

## Verification

- Run the public test command before the measured task.
- Confirm the evaluator can inspect the final diff and test output.

If any check fails, stop. Do not score the run.
