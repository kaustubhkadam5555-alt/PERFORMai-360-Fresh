import logging

from langgraph.graph import END, START, StateGraph

from app.workflows.nodes import (
    bias_auditor_node,
    evidence_retrieval_node,
    feedback_analysis_node,
    finalization_node,
    human_approval_pause_node,
    review_synthesis_node,
    revision_handler_node,
)
from app.workflows.state import MultiAgentWorkflowState

logger = logging.getLogger(__name__)


def route_after_human_pause(state: MultiAgentWorkflowState) -> str:
    """
    Evaluates human approval status:
    - If approved: transitions to finalization
    - If revision requested: transitions to revision handling
    - If awaiting approval (no decision yet) or cancelled: transitions to END (pauses execution)
    """
    decision = state.get("approval_decision")
    status = state.get("status")
    if decision == "approved" or status == "approved":
        return "finalization"
    elif decision == "revision_requested" or status == "revision_requested":
        return "revision_handler"
    else:
        return END


def build_workflow_graph() -> StateGraph:
    """
    Assembles the PERFORMai-360 multi-agent review analysis LangGraph StateGraph.
    Coordinating:
      1. EvidenceRetrievalAgent
      2. FeedbackAnalysisAgent
      3. BiasAuditorAgent
      4. ReviewSynthesisAgent
      5. HumanApprovalPauseNode
      6. FinalizationNode / RevisionHandlerNode
    """
    workflow = StateGraph(MultiAgentWorkflowState)

    # Add agent & decision nodes
    workflow.add_node("evidence_retrieval", evidence_retrieval_node)
    workflow.add_node("feedback_analysis", feedback_analysis_node)
    workflow.add_node("bias_audit", bias_auditor_node)
    workflow.add_node("review_synthesis", review_synthesis_node)
    workflow.add_node("human_approval_pause", human_approval_pause_node)
    workflow.add_node("finalization", finalization_node)
    workflow.add_node("revision_handler", revision_handler_node)

    # Establish linear synthesis flow
    workflow.add_edge(START, "evidence_retrieval")
    workflow.add_edge("evidence_retrieval", "feedback_analysis")
    workflow.add_edge("feedback_analysis", "bias_audit")
    workflow.add_edge("bias_audit", "review_synthesis")
    workflow.add_edge("review_synthesis", "human_approval_pause")

    # Conditional human approval boundary
    workflow.add_conditional_edges(
        "human_approval_pause",
        route_after_human_pause,
        {
            "finalization": "finalization",
            "revision_handler": "revision_handler",
            END: END,
        },
    )

    # Terminal transitions
    workflow.add_edge("finalization", END)
    workflow.add_edge("revision_handler", END)

    return workflow.compile()
