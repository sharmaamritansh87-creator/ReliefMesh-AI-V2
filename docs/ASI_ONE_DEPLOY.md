# Connect ReliefMesh AI to ASI:One and deploy on Agentverse

Checked against the Fetch-A-Thon 3.0 hackpack and the Innovation Lab guides (uagents >= 0.25.5, AgentChatProtocol 0.3.0).
Requirements: **Python 3.10 - 3.13** (Python 3.14 is NOT supported by uagents and crashes with "Event loop is closed").

## 1. Setup (Windows PowerShell)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -c "from uagents_core.contrib.protocols.chat import chat_protocol_spec as s; print(s.name, s.version)"   # AgentChatProtocol 0.3.0
python -m pytest -q
copy .env.example .env      # then edit .env
```
In `.env`: set a private unique `*_SEED` for every agent (any long random phrase), `COORDINATOR_MAILBOX=1`, and
`ASI1_API_KEY` (create at https://asi1.ai/dashboard/api-keys). The ASI:One LLM then understands chat messages,
parses reports and explains plans; without a key the agents fall back to rules.

## 2. Run the agents
```powershell
.\scripts\run_agents.ps1        # 4 worker agents in new windows, Coordinator in this window
```
Leave all windows open. The Coordinator log shows `Agent inspector available at https://agentverse.ai/inspect/?...` and its `agent1q...` address.

## 3. Connect the Coordinator to Agentverse (mailbox)
1. Ctrl+click the **inspector** link (allow Chrome "local network access" if prompted).
2. Click **Connect -> Mailbox -> Finish**. Log should say `Successfully registered as mailbox agent in Agentverse` and `Manifest published successfully: AgentChatProtocol`.
3. In Agentverse > Agents > Local Agents > `reliefmesh-coordinator` > **Overview**: check the README (published from `backend/agents/coordinator_readme.md`; it already has the `innovationlab` and `hackathon` badges), add a clear description and a handle, e.g. `@reliefmesh-ai`.
4. Optional: register the worker agents too (`INTAKE_MAILBOX=1` etc., repeat step 2 for each) so every agent has an Agentverse profile - useful for the multi-agent prize.

## 4. Use it from ASI:One
Open the Coordinator's Agentverse profile > **Chat with Agent** (opens ASI:One chat), or search for the agent's handle in ASI:One. Demo conversation (no custom frontend needed):
1. `run the sample flood scenario`  - 10 reports flow through all agents, plan appears (awaiting approval)
2. `why was Barpeta given the helicopter?` - conflict explanation
3. `road to Dhemaji is blocked` - replan, before/after, re-approval required
4. `avoid the helicopter` - operator change request
5. `approve plan` - only now is anything dispatched

Create the **public shared chat URL** from the ASI:One chat's share option (ask a mentor if you cannot find it).

## 5. Devpost submission checklist (hackpack mandatory items)
- [ ] >= 1 agent registered on Agentverse (Coordinator) - paste each **Agent Profile URL**
- [ ] Agent Chat Protocol implemented (done) and `publish_manifest=True` (done)
- [ ] Discoverable + usable in ASI:One, full workflow inside the chat
- [ ] Public ASI:One shared chat URL showing the whole workflow
- [ ] Public GitHub repo; README lists agent **names and addresses** (fill the table in README.md) and has both badges
- [ ] Demo video **3-5 minutes** (record the ASI:One chat, not the code editor)
- [ ] Description: problem, target users (district administration, NDRF/SDRF, NGOs, volunteers), outcome (human-approved relief plan)
- [ ] Keep the agents RUNNING until judging ends (laptop awake, stable internet). Workers use local endpoints, so run them on the same machine as the Coordinator.

## 6. Bonus items still open (optional)
- ASI1 Interactive Cards (forms / review screen for plan approval): https://innovationlab.fetch.ai/resources/docs/interactive-cards/asi-interactive-cards
- Payment Protocol (credible monetisation): https://innovationlab.fetch.ai/resources/docs/agent-transaction/agent-payment-protocol

## 7. Troubleshooting
| Symptom | Fix |
|---|---|
| `RuntimeError: Event loop is closed` / `Agent(...)` fails | Python 3.14. Recreate venv with 3.12. |
| ASI:One cannot find / reach the agent | Coordinator must be running, mailbox connected (step 3), manifest published. |
| Chat says sub-agent did not respond | A worker window is closed. Plan is still computed locally (recovery path). |
| `401 invalid_api_key` in logs | Wrong `ASI1_API_KEY`; regenerate. The agent keeps working with rules. |
| Addresses changed | Seeds changed. Keep `.env` seeds fixed and update the README table. |
