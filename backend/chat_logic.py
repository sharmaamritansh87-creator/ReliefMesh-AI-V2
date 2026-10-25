"""Natural-language handling for the Coordinator's ASI:One chat (pure Python, unit-testable).

Intent understanding uses the ASI:One LLM when ASI1_API_KEY is set, otherwise deterministic rules.
"""
import re
from typing import Dict, List, Optional

from . import pipeline as pl
from .llm import enabled as llm_enabled, llm_intent
from .logic.coordination import ApprovalError
from .state import DISCLAIMER, ReliefState

HELP = ("**ReliefMesh AI** - multi-agent flood relief coordinator for North East India (SIMULATED data).\n"
        "Try:\n- `run the sample flood scenario`\n- `report flooding in Majuli, 150 people need food`\n"
        "- `show current plan`\n- `road to Dhemaji is blocked`\n- `avoid the helicopter`\n- `why was Barpeta given the helicopter?`\n"
        "- `approve plan`\n\n_" + DISCLAIMER + "_")

ALIASES = {"garo": "West Garo Hills", "tura": "West Garo Hills", "siang": "East Siang",
           "pasighat": "East Siang", "katigorah": "Cachar"}
VEHICLE_WORDS = {"heli": ["Heli-1"], "boat": ["Boat-1", "Boat-2"], "truck": ["Truck-1"]}


def village_names(s: ReliefState) -> List[str]:
    return [n["id"] for n in s.cfg["ne_graph"]["nodes"] if n["kind"] == "village"]


def find_village(s: ReliefState, text: str) -> Optional[dict]:
    t = text.lower()
    nodes = {n["id"]: n for n in s.cfg["ne_graph"]["nodes"] if n["kind"] == "village"}
    for name in sorted(nodes, key=len, reverse=True):
        if name.lower() in t:
            return nodes[name]
    for alias, name in ALIASES.items():
        if alias in t and name in nodes:
            return nodes[name]
    return None


def rule_intent(s: ReliefState, text: str) -> Dict:
    t = text.lower().strip()
    village = find_village(s, text)
    v = village["id"] if village else None
    exclude = [x for k, ids in VEHICLE_WORDS.items() if re.search(rf"\b{k}\w*", t) for x in ids]
    if not t or (len(t) < 25 and re.search(r"\b(help|hi|hello|hey)\b", t)):
        return {"intent": "help", "village": v, "exclude_vehicles": []}
    if re.search(r"\b(reset|start over|clear all)\b", t):
        return {"intent": "reset", "village": v, "exclude_vehicles": []}
    if re.search(r"\b(approve|approved|go ahead|confirm plan|dispatch now)\b", t) and not re.search(r"\bnot approve|don'?t approve", t):
        return {"intent": "approve", "village": v, "exclude_vehicles": []}
    if re.search(r"(request changes|change the plan|change plan|\bavoid\b|\bwithout\b|\bno (heli|boat|truck))", t) and exclude:
        return {"intent": "request_changes", "village": v, "exclude_vehicles": exclude}
    if re.search(r"\b(block|blocked|blockage|washed away|cut off|closed|impassable)\b", t):
        return {"intent": "block", "village": v, "exclude_vehicles": []}
    if re.search(r"\b(sample|demo|simulate|simulation|scenario|all reports|10 reports|load)\b", t):
        return {"intent": "load_sample", "village": v, "exclude_vehicles": []}
    if re.search(r"\b(why|explain|reason|conflict|conflicts)\b", t):
        return {"intent": "explain", "village": v, "exclude_vehicles": []}
    if village and (re.search(r"\d", t) or re.search(r"\b(need|needs|food|water|medic\w*|rescue|stranded|flood\w*|landslide|shelter|help|urgent|evacuat\w*)\b", t)):
        return {"intent": "report", "village": v, "exclude_vehicles": []}
    if re.search(r"\b(show|display|status|current|plan|summary)\b", t):
        return {"intent": "show_plan", "village": v, "exclude_vehicles": []}
    return {"intent": "help", "village": v, "exclude_vehicles": []}


def understand(s: ReliefState, text: str) -> Dict:
    """ASI:One LLM first (if configured), deterministic rules as fallback."""
    if llm_enabled():
        r = llm_intent(text, village_names(s))
        # sanity-check the LLM: an intent without what it needs falls back to the deterministic rules
        valid = bool(r) and not (r["intent"] == "request_changes" and not r["exclude_vehicles"]) \
            and not (r["intent"] == "block" and not r["village"]) \
            and not (r["intent"] == "report" and not (r["village"] or find_village(s, text)))
        if valid:
            r["source"] = "asi1-llm"
            return r
    r = rule_intent(s, text)
    r["source"] = "rules"
    return r


def plan_text(s: ReliefState) -> str:
    p = s.plan
    if not p:
        return "No plan yet. Say `run the sample flood scenario` or report an emergency, e.g. `report flooding in Majuli, 150 people need food`."
    status = {"pending_approval": "AWAITING HUMAN APPROVAL", "approved": "APPROVED - DISPATCHED"}.get(p["status"], p["status"])
    lines = [f"**Relief plan v{p['version']} - {status}**", p["explanation"], ""]
    for i in p["items"]:
        if i["status"] == "planned":
            lines.append(f"- **{i['village']}** ({i['priority']}) -> {i['vehicle_id']} via {i['mode']}, ETA {i['eta_label']}, "
                         f"{i['volunteers']} volunteers" + (" - dispatched" if i["dispatched"] else ""))
        else:
            lines.append(f"- **{i['village']}** ({i['priority']}) -> {i['status']}: {i['notes']}")
    for c in p["conflicts"]:
        lines.append(f"\nConflict on {c['resource']}: {c['resolution']}")
    if p["shortages"]:
        lines.append("\nShortages: " + ", ".join(f"{k} {v}" for k, v in p["shortages"].items()))
    if s.blocked_events:
        lines.append("Blocked: " + "; ".join(s.blocked_events))
    if p["status"] == "pending_approval":
        lines.append("\nReply **approve plan** to release dispatch, or ask for changes (e.g. `avoid the helicopter`).")
    return "\n".join(lines + ["", f"_{DISCLAIMER}_"])


def explain_text(s: ReliefState) -> str:
    if not s.plan:
        return "No plan yet."
    out = ["**Why the plan looks like this**", "- Sites are ranked by urgency, then headcount, then report confidence.",
           "- Each vehicle serves sites one after another, so ETA includes queue time.",
           "- The fastest ground vehicle goes to the higher-priority site; others get a boat via river, a queue slot, or the helicopter as a last resort."]
    out += [f"- {c['resolution']}" for c in s.plan["conflicts"]] or ["- No vehicle conflicts in this plan."]
    out += [f"- {m}" for m in s.merge_log]
    return "\n".join(out)


def execute(s: ReliefState, intent: Dict, raw_text: str = "") -> Dict:
    """Run the intent. Returns {"text": reply, "chain": bool}; chain=True means send reports through the agent chain."""
    i = intent["intent"]
    if i == "help":
        return {"text": HELP, "chain": False}
    if i == "reset":
        s.reset()
        return {"text": "State reset. Ready for new reports.", "chain": False}
    if i == "load_sample":
        s.reset()
        pl.load_seed_reports(s)
        return {"text": f"Loaded {len(s.raw_reports)} simulated reports (English / Hinglish / Assamese) and ran them through the Intake -> Verification -> Resource -> Routing agents.", "chain": True}
    if i == "report":
        node = next((n for n in s.cfg["ne_graph"]["nodes"] if n["id"] == intent.get("village")), None) or find_village(s, raw_text)
        if not node:
            return {"text": "Which village is this about? Mention one of: " + ", ".join(village_names(s)), "chain": False}
        pl.add_report(s, {"text": raw_text, "village": node["id"], "district": node["id"], "state": node["state"],
                          "lat": node["lat"], "lon": node["lon"]})
        return {"text": f"Report logged for {node['id']} and processed by the Intake -> Verification -> Resource -> Routing agents.", "chain": True}
    if i == "show_plan":
        return {"text": plan_text(s), "chain": False}
    if i == "explain":
        return {"text": explain_text(s), "chain": False}
    if i == "approve":
        try:
            s.approve()
            return {"text": "Plan approved by the human operator. Dispatch orders released.\n\n" + plan_text(s), "chain": False}
        except ApprovalError as e:
            return {"text": f"Cannot approve: {e}", "chain": False}
    if i == "request_changes":
        try:
            pl.request_changes(s, raw_text, intent.get("exclude_vehicles") or [])
        except ValueError as e:
            return {"text": str(e), "chain": False}
        return {"text": "Plan recomputed with your constraints.\n\n" + plan_text(s), "chain": False}
    if i == "block":
        village = intent.get("village")
        if not village:
            return {"text": "Which village's road is blocked? e.g. `road to Dhemaji is blocked`.", "chain": False}
        if not s.plan:
            pl.load_seed_reports(s)
            pl.run_all(s)
        try:
            pl.block_road(s, {"village": village})
        except ValueError as e:
            return {"text": str(e), "chain": False}
        return {"text": f"Road to {village} marked blocked. Routing and Resource agents recomputed; the plan needs re-approval.\n\n" + plan_text(s), "chain": False}
    return {"text": HELP, "chain": False}
