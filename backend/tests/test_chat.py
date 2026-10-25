"""ASI:One chat commands: intent rules and an end-to-end conversation without any custom frontend."""
import pytest

from backend import pipeline as p
from backend.chat_logic import execute, plan_text, rule_intent
from backend.state import ReliefState


@pytest.fixture()
def s():
    return ReliefState(persist=False)


@pytest.mark.parametrize("text,intent", [
    ("hello", "help"),
    ("run the sample flood scenario", "load_sample"),
    ("report flooding in Majuli, 150 people need food", "report"),
    ("Dhemaji me 200 log fase hain, khana chahiye", "report"),
    ("road to Dhemaji is blocked", "block"),
    ("show current plan", "show_plan"),
    ("avoid the helicopter", "request_changes"),
    ("why was Barpeta given the helicopter?", "explain"),
    ("approve plan", "approve"),
    ("reset", "reset"),
])
def test_rule_intents(s, text, intent):
    assert rule_intent(s, text)["intent"] == intent


def test_village_and_vehicle_extraction(s):
    assert rule_intent(s, "road to Dhemaji is blocked")["village"] == "Dhemaji"
    assert rule_intent(s, "avoid the helicopter")["exclude_vehicles"] == ["Heli-1"]
    assert rule_intent(s, "Garo Hills landslide 40 people need medicine")["village"] == "West Garo Hills"


def test_full_conversation_inside_chat(s):
    out = execute(s, rule_intent(s, "run the sample flood scenario"), "run the sample flood scenario")
    assert out["chain"] and len(s.raw_reports) == 10
    p.run_all(s)  # what the agent chain does
    assert "AWAITING HUMAN APPROVAL" in plan_text(s)
    out = execute(s, rule_intent(s, "road to Dhemaji is blocked"), "")
    assert "re-approval" in out["text"] and s.plan["status"] == "pending_approval"
    out = execute(s, rule_intent(s, "avoid the helicopter"), "avoid the helicopter")
    assert all(i["vehicle_id"] != "Heli-1" for i in s.plan["items"])
    assert not any(i["dispatched"] for i in s.plan["items"])
    out = execute(s, rule_intent(s, "approve plan"), "")
    assert "approved" in out["text"].lower() and any(i["dispatched"] for i in s.plan["items"])
    assert "Cannot approve" in execute(s, rule_intent(s, "approve plan"), "")["text"]


def test_single_report_via_chat(s):
    txt = "report flooding in Majuli, 150 people need food"
    assert execute(s, rule_intent(s, txt), txt)["chain"]
    p.run_all(s)
    assert s.plan["items"][0]["village"] == "Majuli"


def test_block_without_village_asks(s):
    assert "Which village" in execute(s, rule_intent(s, "the road is blocked"), "")["text"]


def test_bad_llm_intent_falls_back_to_rules(s):
    from backend import chat_logic as cl
    old = (cl.llm_enabled, cl.llm_intent)
    cl.llm_enabled = lambda: True
    cl.llm_intent = lambda text, v: {"intent": "request_changes", "village": None, "exclude_vehicles": []}
    try:
        r = cl.understand(s, "road to Dhemaji is blocked")
    finally:
        cl.llm_enabled, cl.llm_intent = old
    assert r["intent"] == "block" and r["source"] == "rules"
