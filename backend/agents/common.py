"""Shared helpers for the five uAgents: creation, deterministic addresses, local vs Agentverse (mailbox) mode.

Env:
  <NAME>_SEED       private seed phrase per agent (addresses derive from it)
  <NAME>_MAILBOX=1  connect that agent to Agentverse via mailbox (or MAILBOX=1 for all)
  <NAME>_ADDRESS    override a peer's address (agent1q...)
Requires Python 3.10-3.13 and uagents>=0.25.5 (Python 3.14 is not supported by uagents).
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass

from uagents import Agent
from uagents.crypto import Identity

PORTS = {"intake": 8101, "verification": 8102, "resource": 8103, "routing": 8104, "coordinator": 8105}


def seed_of(name: str) -> str:
    """Seed phrase per agent. Set <NAME>_SEED in .env - the default is public in the repo."""
    return os.getenv(f"{name.upper()}_SEED", f"reliefmesh-{name}-demo-seed-change-me")


def address_of(name: str) -> str:
    """Peer address. Set <NAME>_ADDRESS to override; otherwise derived from the seed."""
    return os.getenv(f"{name.upper()}_ADDRESS") or Identity.from_seed(seed_of(name), 0).address


def use_mailbox(name: str) -> bool:
    return os.getenv(f"{name.upper()}_MAILBOX", os.getenv("MAILBOX", "0")) == "1"


def make_agent(name: str, readme: str = "") -> Agent:
    kw = dict(name=f"reliefmesh-{name}", seed=seed_of(name), port=PORTS[name])
    if use_mailbox(name):
        kw.update(mailbox=True, publish_agent_details=True)
        if readme:
            kw["readme_path"] = str(Path(__file__).with_name(readme))
    else:
        kw["endpoint"] = [f"http://127.0.0.1:{PORTS[name]}/submit"]
    return Agent(**kw)
