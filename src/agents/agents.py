from dataclasses import dataclass
from typing import Any

from langgraph.graph.state import CompiledStateGraph
from langgraph.pregel import Pregel

from agents.audit_agent import audit_ledger_agent
from agents.detector import detector_agent
from agents.governor import governor_agent
from agents.orchestrator import orchestrator, recovery_agent_graph
from agents.strategist import strategist_agent
from agents.voice_recovery import voice_recovery_agent
from schema import AgentInfo

DEFAULT_AGENT = "revenue-recovery-orchestrator"

AgentGraph = CompiledStateGraph | Pregel | Any


@dataclass
class Agent:
    description: str
    graph_like: AgentGraph


agents: dict[str, Agent] = {
    "revenue-recovery-orchestrator": Agent(
        description="Master autonomous multi-agent revenue recovery engine for payment failures, dropoffs, and B2B receivables.",
        graph_like=recovery_agent_graph,
    ),
    "hinglish-voice-agent": Agent(
        description="Conversational Hinglish Voice AI recovery agent for high-ticket purchases and overdue receivables.",
        graph_like=recovery_agent_graph,
    ),
    "b2b-receivables-chaser": Agent(
        description="Specialized B2B aging invoice chaser and Promise-to-Pay negotiator.",
        graph_like=recovery_agent_graph,
    ),
    "mandate-retry-sequencer": Agent(
        description="Smart recurring e-mandate and subscription dunning optimizer with RBI compliance.",
        graph_like=recovery_agent_graph,
    ),
}


async def load_agent(agent_id: str) -> None:
    """Load agent if needed."""
    pass


def get_agent(agent_id: str) -> AgentGraph:
    """Get an agent graph."""
    if agent_id not in agents:
        agent_id = DEFAULT_AGENT
    return agents[agent_id].graph_like


def get_all_agent_info() -> list[AgentInfo]:
    return [
        AgentInfo(key=agent_id, description=agent.description)
        for agent_id, agent in agents.items()
    ]


__all__ = [
    "DEFAULT_AGENT",
    "Agent",
    "AgentGraph",
    "agents",
    "get_agent",
    "get_all_agent_info",
    "load_agent",
    "orchestrator",
    "detector_agent",
    "strategist_agent",
    "governor_agent",
    "audit_ledger_agent",
    "voice_recovery_agent",
]
