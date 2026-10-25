"""Coordinator Agent: orchestrates the pipeline, resolves conflicts, WAITS for human approval and
exposes the Agent Chat Protocol so ASI:One can discover and talk to it.

Flow for a report from ASI:One (ONE reply per user message):
  chat -> Coordinator -> Intake -> Verification -> Resource -> Routing -> Coordinator -> single reply with the plan.
If a sub-agent does not answer within CHAIN_TIMEOUT_S the Coordinator computes the plan locally (recovery).
"""
import os
import time
import uuid
from datetime import datetime, timezone

from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (ChatAcknowledgement, ChatMessage, EndSessionContent,
                                                 StartSessionContent, TextContent, chat_protocol_spec)

from .. import pipeline as pl
from ..chat_logic import HELP, execute, plan_text, understand
from ..models import RawBatch, RawReport, RoutedBatch, dump
from ..state import get_state
from .common import address_of, make_agent

CHAIN_MODE = os.getenv("CHAIN_MODE", "1") == "1"       # 0 = compute locally, skip the sub-agents
CHAIN_TIMEOUT_S = float(os.getenv("CHAIN_TIMEOUT_S", "15"))
MAX_MSGS, WINDOW_S = 6, 20.0                            # loop guard: max messages per sender per window

agent = make_agent("coordinator", readme="coordinator_readme.md")
chat_proto = Protocol(spec=chat_protocol_spec)
_recent: dict = {}


def _throttled(sender: str) -> bool:
    now = time.time()
    q = [t for t in _recent.get(sender, []) if now - t < WINDOW_S] + [now]
    _recent[sender] = q
    return len(q) > MAX_MSGS


def _reply(text: str) -> ChatMessage:
    """Final reply for a turn. State lives in the Coordinator, so each turn can end its session."""
    return ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid.uuid4(),
                       content=[TextContent(type="text", text=text), EndSessionContent(type="end-session")])


@chat_proto.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id))
    if _throttled(sender):
        ctx.logger.warning(f"[coordinator] too many messages from {sender[:14]}...; ignoring (loop guard)")
        return
    s = get_state()
    text = " ".join(c.text for c in msg.content if isinstance(c, TextContent)).strip()
    if not text:
        if any(isinstance(c, StartSessionContent) for c in msg.content):
            await ctx.send(sender, _reply(HELP))
        return
    intent = understand(s, text)
    ctx.logger.info(f"[coordinator] intent={intent['intent']} via {intent['source']} | text={text[:100]!r}")
    out = execute(s, intent, text)
    if not out["chain"]:
        await ctx.send(sender, _reply(out["text"]))
    elif CHAIN_MODE:
        run_id = uuid.uuid4().hex[:8]
        s.pending_chat[run_id] = {"sender": sender, "ts": time.time(), "intro": out["text"]}
        await ctx.send(address_of("intake"), RawBatch(run_id=run_id, reports=[RawReport(**r) for r in s.raw_reports]))
        # the single reply is sent by on_routed (or by the watchdog if the chain is silent)
    else:
        pl.run_all(s)
        await ctx.send(sender, _reply(out["text"] + "\n\n" + plan_text(s)))


@chat_proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"ack from {sender[:14]}... for {msg.acknowledged_msg_id}")


@agent.on_message(model=RoutedBatch)
async def on_routed(ctx: Context, sender: str, msg: RoutedBatch):
    """Final hop: resolve conflicts, build the plan, then wait for approval (never auto-dispatch)."""
    s = get_state()
    with s.lock:
        s.verified = [dump(r) for r in msg.requests]
        s.allocations = [dump(a) for a in msg.allocations]
        s.fleet = [dump(v) for v in msg.fleet]
        s.routes = [dump(r) for r in msg.routes]
        pl.stage_coordinate(s)
    ctx.logger.info(f"[coordinator] plan v{s.plan['version']} ready, awaiting human approval")
    info = s.pending_chat.pop(msg.run_id, None)
    if info:
        await ctx.send(info["sender"], _reply(info["intro"] + "\n\n" + plan_text(s)))


@agent.on_interval(period=3.0)
async def watchdog(ctx: Context):
    """Recovery: if the agent chain is silent, compute locally so the chat never hangs."""
    s = get_state()
    for run_id, info in list(s.pending_chat.items()):
        if time.time() - info["ts"] > CHAIN_TIMEOUT_S:
            s.pending_chat.pop(run_id, None)
            ctx.logger.warning(f"[coordinator] run {run_id} timed out waiting for sub-agents; computing locally")
            pl.run_all(s)
            await ctx.send(info["sender"], _reply(info["intro"] + "\n\n_A sub-agent did not respond in time, so the Coordinator computed the plan locally._\n\n" + plan_text(s)))


agent.include(chat_proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
