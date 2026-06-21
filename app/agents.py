import json
import os
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langchain_azure_ai.chat_models import AzureAIChatModel
from azure.identity import DefaultAzureCredential

class AgencyState(TypedDict):
    client_profile: dict
    market_intelligence: dict
    creative_assets: dict
    deployment_status: dict
    human_feedback: dict
    validation_errors: list

# Initialize Foundry client
credential = DefaultAzureCredential()
llm = AzureAIChatModel(
    model="gpt-4.1",
    endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
    credential=credential,
)

def orchestrator_node(state: AgencyState) -> AgencyState:
    """Master Orchestrator — breaks down the client brief."""
    # Implementation here
    return state

def researcher_node(state: AgencyState) -> AgencyState:
    """Strategic Researcher — analyzes market and competitors."""
    return state

def creative_node(state: AgencyState) -> AgencyState:
    """Creative Agent — generates copy and visuals."""
    return state

def human_review_node(state: AgencyState) -> AgencyState:
    """Human-in-the-Loop gate — pauses for approval."""
    # This node acts as a pass-through; the graph interrupts before it
    return state

def launch_node(state: AgencyState) -> AgencyState:
    """Launch Agent — deploys to Google/Meta APIs."""
    return state

def should_continue(state: AgencyState) -> Literal["launch", "creative"]:
    """Conditional routing based on human feedback."""
    if state.get("human_feedback", {}).get("status") == "APPROVED":
        return "launch"
    return "creative"

# Build the graph
workflow = StateGraph(AgencyState)
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("creative", creative_node)
workflow.add_node("human_review", human_review_node)
workflow.add_node("launch", launch_node)

workflow.set_entry_point("orchestrator")
workflow.add_edge("orchestrator", "researcher")
workflow.add_edge("researcher", "creative")
workflow.add_edge("creative", "human_review")
workflow.add_conditional_edges("human_review", should_continue, {
    "launch": "launch",
    "creative": "creative"
})
workflow.add_edge("launch", END)

# Compile with interrupt before human_review
graph = workflow.compile(interrupt_before=["human_review"])