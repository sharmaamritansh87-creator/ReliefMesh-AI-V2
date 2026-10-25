"""Optional LLM helpers (ASI:One or any OpenAI-compatible API). Everything falls back to rules."""
import json
import os
import urllib.request
from typing import Optional


def _key() -> str:
    """ASI1_API_KEY (Fetch docs name) or LLM_API_KEY (any OpenAI-compatible provider)."""
    return os.getenv("ASI1_API_KEY") or os.getenv("LLM_API_KEY") or ""


def enabled() -> bool:
    return bool(_key())


def _chat(system: str, user: str, max_tokens: int = 300) -> Optional[str]:
    if not enabled():
        return None
    base = os.getenv("LLM_BASE_URL", "https://api.asi1.ai/v1").rstrip("/")
    body = json.dumps({"model": os.getenv("LLM_MODEL", "asi1"), "max_tokens": max_tokens,
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(f"{base}/chat/completions", data=body, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {_key()}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def llm_parse_report(text: str) -> Optional[dict]:
    """Return {needs, people, urgency} or None."""
    out = _chat("Extract a disaster report. Reply ONLY with JSON: "
                '{"needs":[subset of food,water,medical,evacuation,rescue,shelter],'
                '"people":int,"urgency":1-5}. The text may be English, Hindi or Assamese in Latin script.', text)
    if not out:
        return None
    try:
        d = json.loads(out[out.index("{"): out.rindex("}") + 1])
        valid = {"food", "water", "medical", "evacuation", "rescue", "shelter"}
        needs = [n for n in d.get("needs", []) if n in valid]
        if not needs:
            return None
        return {"needs": needs, "people": max(1, int(d.get("people", 10))),
                "urgency": min(5, max(1, int(d.get("urgency", 3))))}
    except Exception:
        return None


def llm_explain(summary: str) -> Optional[str]:
    return _chat("You are a disaster-relief coordinator. In 2 plain sentences explain this plan to a "
                 "district officer. Mention that human approval is required.", summary, 150)


INTENTS = ("help", "reset", "load_sample", "report", "show_plan", "block", "approve", "request_changes", "explain")


def llm_intent(text: str, villages: list) -> Optional[dict]:
    """Use the ASI:One LLM to understand a chat message. Returns {intent, village, exclude_vehicles} or None."""
    out = _chat(
        "You route messages for a disaster-relief coordinator agent. Reply ONLY with JSON: "
        '{"intent": one of ' + ", ".join(INTENTS) + ', "village": one of ' + json.dumps(villages) +
        ' or null, "exclude_vehicles": subset of ["Truck-1","Boat-1","Boat-2","Heli-1"]}. '
        "report = a new flood/landslide request for help; load_sample = run the simulated 10-report scenario; "
        "block = a road is blocked; request_changes = operator wants the plan changed; "
        "approve = operator approves/dispatches; show_plan/explain = asks about the current plan.", text, 120)
    if not out:
        return None
    try:
        d = json.loads(out[out.index("{"): out.rindex("}") + 1])
        if d.get("intent") not in INTENTS:
            return None
        v = d.get("village")
        return {"intent": d["intent"], "village": v if v in villages else None,
                "exclude_vehicles": [x for x in d.get("exclude_vehicles", []) if x in ("Truck-1", "Boat-1", "Boat-2", "Heli-1")]}
    except Exception:
        return None
