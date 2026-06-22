import os
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama  # <--- NEW IMPORT

class AgencyState(TypedDict):
    client_profile: dict
    market_intelligence: dict
    creative_assets: dict
    deployment_status: dict
    human_feedback: dict
    validation_errors: list

# Initialize local LLM
llm = ChatOllama(
    model="llama3.2:3b",      # Change if you pulled a different model
    base_url="http://localhost:11434",
    temperature=0.7,
)

def orchestrator_node(state: AgencyState) -> AgencyState:
    # Your logic here
    return state

def researcher_node(state: AgencyState) -> AgencyState:
    return state

def creative_node(state: AgencyState) -> AgencyState:
    return state

def human_review_node(state: AgencyState) -> AgencyState:
    return state

def launch_node(state: AgencyState) -> AgencyState:
    return state

def should_continue(state: AgencyState) -> Literal["launch", "creative"]:
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

graph = workflow.compile(interrupt_before=["human_review"])