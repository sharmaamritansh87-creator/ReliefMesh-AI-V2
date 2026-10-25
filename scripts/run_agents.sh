#!/usr/bin/env bash
# macOS / Linux: worker agents in the background, Coordinator (mailbox) in the foreground. Run from repo root with venv active.
export COORDINATOR_MAILBOX=1
for a in intake verification resource routing; do python -m backend.agents.${a}_agent & done
sleep 5
python -m backend.agents.coordinator_agent
