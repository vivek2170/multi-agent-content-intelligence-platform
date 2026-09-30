import asyncio
import logging
from langgraph.graph import StateGraph, END
from typing import Dict, Any, TypedDict
from ..agents.planner import PlannerAgent
from ..agents.researcher import ResearcherAgent
from ..agents.fact_checker import FactCheckerAgent
from ..agents.writer import WriterAgent
from ..agents.editor import EditorAgent
from ..agents.final_fact_checker import FinalFactCheckerAgent

logger = logging.getLogger("workflow")

class WorkflowState(TypedDict, total=False):
    run_id: str
    request: Dict[str, Any]
    plan: Dict[str, Any]
    research: Dict[str, Any]
    drafts: list
    editor_feedback: Dict[str, Any]
    revision_count: int
    max_revisions: int
    quality_score: float
    final_content: str
    sources: list
    metrics: list
    errors: list
    status: str
    current_agent: str
    current_iteration: int

class ContentWorkflow:
    def __init__(self, llm_provider, search_provider, config: Dict[str, Any]):
        self.llm = llm_provider
        self.search = search_provider
        self.config = config
        self.planner = PlannerAgent(llm_provider, search_provider, config)
        self.researcher = ResearcherAgent(llm_provider, search_provider, config)
        self.fact_checker = FactCheckerAgent(llm_provider, search_provider, config)
        self.writer = WriterAgent(llm_provider, search_provider, config)
        self.editor = EditorAgent(llm_provider, search_provider, config)
        self.final_fact_checker = FinalFactCheckerAgent(llm_provider, search_provider, config)
        self.graph = self._build()

    def _build(self):
        g = StateGraph(WorkflowState)
        g.add_node("planner", self.planner.run)
        g.add_node("researcher", self.researcher.run)
        g.add_node("fact_checker", self.fact_checker.run)
        g.add_node("writer", self.writer.run)
        g.add_node("editor", self.editor.run)
        g.add_node("final_fact_checker", self.final_fact_checker.run)
        g.set_entry_point("planner")
        g.add_edge("planner", "researcher")
        g.add_edge("researcher", "fact_checker")
        g.add_edge("fact_checker", "writer")
        g.add_edge("writer", "editor")
        g.add_conditional_edges("editor", self._route_editor, {
            "revise": "writer",
            "final": "final_fact_checker"
        })
        g.add_edge("final_fact_checker", END)
        return g.compile()

    def _route_editor(self, state: WorkflowState):
        if state.get("status") == "REVISION_REQUIRED":
            return "revise"
        return "final"

    async def execute(self, run_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        state: WorkflowState = {
            "run_id": run_id,
            "request": request,
            "plan": {},
            "research": {},
            "drafts": [],
            "editor_feedback": {},
            "revision_count": 0,
            "max_revisions": self.config.get("MAX_REVISIONS", 3),
            "quality_score": 0.0,
            "final_content": "",
            "sources": [],
            "metrics": [],
            "errors": [],
            "status": "CREATED",
            "current_agent": "planner",
            "current_iteration": 0,
        }
        timeout = self.config.get("WORKFLOW_TIMEOUT_SECONDS", 600)
        logger.info("workflow start run_id=%s timeout=%s", run_id, timeout)
        try:
            result = await asyncio.wait_for(
                self.graph.ainvoke(state),
                timeout=timeout,
            )
            logger.info("workflow completed run_id=%s status=%s", run_id, result.get("status"))
            return dict(result)
        except asyncio.TimeoutError:
            logger.error("workflow timeout run_id=%s", run_id)
            state["status"] = "FAILED"
            state["errors"].append(f"Workflow timed out after {timeout} seconds")
            return dict(state)
