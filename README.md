![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

# ReliefMesh AI - Multi-Agent Disaster Response (North East India)

> **SIMULATED DEMO DATA - NOT A REAL EMERGENCY.** Decision-support only. A human must approve the plan before any real-world dispatch.

Flood/landslide reports arrive messy and duplicated while supplies, vehicles and volunteers are limited.
ReliefMesh AI turns them into a coordinated, human-approved plan:
**Reports -> Verify -> Allocate -> Plan routes -> Resolve conflicts -> Human approval -> Action.**

Five Fetch.ai **uAgents** (Intake, Verification, Resource, Routing, Coordinator) pass typed Models to each other.
The Coordinator speaks the **Chat Protocol**, so it can be deployed to **Agentverse** and used from **ASI:One**.
Runs locally with **no paid API keys** (an LLM is optional).

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # optional
python -m backend.run_all                              # API on :8080 + all 5 agents in one Bureau

# second terminal
cd frontend && npm i && npm run dev                    # http://localhost:5173
```
Tests: `python -m pytest -q` (dedupe, conflicts, rerouting on a blocked edge, approval gate).

## Demo 
Open the dashboard -> **Start Demo** -> **Next Step** x7. Or click **Simulate Road Blocked** for the replanning moment,
then **Approve Plan**. Script: `docs/demo_script.md`. Architecture: `docs/architecture.md`.

## API
| Method | Path | Purpose |
|---|---|---|
| POST | /reports | add a report and re-run the pipeline |
| POST | /reports/seed | load the 10 seed reports and run all agents |
| GET | /state | full dashboard state |
| GET | /graph | nodes and road/river edges |
| POST | /events/road-blocked | `{"village":"Dhemaji"}` or `{"from":"Lakhimpur","to":"Dhemaji"}` |
| POST | /plan/approve | the **only** way anything becomes "dispatched" |
| POST | /plan/request-changes | `{"note":"...","exclude_vehicles":["Heli-1"]}` |
| POST | /demo/start, /demo/step, /demo/reset | scripted 8-step demo |
| GET | /agents/log | inter-agent message feed |
| GET | /stream | SSE snapshots |

## ASI:One + Agentverse 
Full guide: [`docs/ASI_ONE_DEPLOY.md`](docs/ASI_ONE_DEPLOY.md). Quick version (needs **Python 3.10-3.13**, not 3.14):
```bash
pip install -r requirements.txt && cp .env.example .env     # set seeds + ASI1_API_KEY
./scripts/run_agents.sh            # Windows: .\scripts\run_agents.ps1
# open the Coordinator's "Agent inspector" link -> Connect -> Mailbox -> Finish
# Agentverse > your agent > Chat with Agent  (opens ASI:One)
```
In ASI:One: `run the sample flood scenario` -> `road to Dhemaji is blocked` -> `avoid the helicopter` -> `approve plan`.

### Agents
| Agent | Name | Address | Role |
|---|---|---|---|
| Coordinator | reliefmesh-coordinator | `a89d3f0ed8eec4c453922243c98d3eca` | ASI:One chat (Agent Chat Protocol), conflicts, approval gate |
| Intake | reliefmesh-intake | `ebe610ab5b31947775a36b83d1b61eee` | parse multilingual reports |
| Verification | reliefmesh-verification | `098063c368aa4c28a61906266be1f675` | dedupe, conflicts, confidence |
| Resource | reliefmesh-resource | `1b593349277957309c7fb6b9da8137e6` | supplies, volunteers, vehicles, shortages |
| Routing | reliefmesh-routing | `522ab57a552591ca8d2b4be90b9f7be2` | NetworkX road/river/air routes |

Agentverse profile URL: https://agentverse.ai/agents/details/agent1qfxn2d6kupa3zulgfyrmf7dmszq2eet73hd5a29n5cxxk75alkuc5rkatph/profile | ASI:One shared chat: https://asi1.ai/shared-chat/42a9ea90-c770-4449-89f3-aedf484d8363

## ASI:One LLM
Set `ASI1_API_KEY` (https://asi1.ai/dashboard/api-keys) so the ASI:One LLM understands chat messages, parses reports and explains plans. Without it, deterministic rules are used. Any OpenAI-compatible provider works via `LLM_API_KEY`/`LLM_BASE_URL`.

## Add another region (Odisha, Kerala, Bihar...)
Copy `data/` to `data_odisha/`, edit `ne_graph.json` (nodes, road/river edges, air hubs), `reports.json`, `inventory.json`, `teams.json`, then `RELIEF_DATA_DIR=./data_odisha python -m backend.run_all`. No code changes.

## Layout
```
backend/  models.py graph.py scoring.py llm.py state.py pipeline.py demo.py run_all.py
          logic/   (pure, testable agent logic)   agents/ (uAgents wrappers)   app/main.py (FastAPI)   tests/
data/     reports.json inventory.json teams.json ne_graph.json
frontend/ React + Vite + Tailwind + Leaflet dashboard
docs/     architecture.md slides_outline.md demo_script.md
```

