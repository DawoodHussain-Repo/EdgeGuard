# AI Workflow Rules - EdgeGuard-AI

## Approach

- Build incrementally using a spec-driven workflow.
- Update `context/progress-tracker.md` after each completed milestone.
- Commit code to Git at logical milestones with clear, descriptive commit messages.

## Scoping Rules

- Work on one component milestone at a time (Context -> Engine -> Vision Stream -> FastAPI -> Web UI -> Docker/Docs).
- Verify each phase before proceeding to the next.

## Git Workflow

- Repository remote: `https://github.com/DawoodHussain-Repo/EdgeGuard.git`.
- Primary branch: `main`.
- Commit after each key milestone:
  1. `docs: initialize project context & architectural specifications`
  2. `feat: implement Pydantic schemas and spatial PPE rules engine`
  3. `feat: implement YOLO + ByteTrack vision pipeline & streaming service`
  4. `feat: implement interactive dark-mode telemetry dashboard UI`
  5. `chore: add Docker container configuration & project documentation`

## Verification Requirements

- Python code must pass syntax checks (`python -m py_compile`).
- FastAPI server must initialize and respond on `/api/v1/telemetry` and `/api/v1/health`.
- Web UI must load and stream live video without console errors.
