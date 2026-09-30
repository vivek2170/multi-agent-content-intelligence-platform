from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class Platform(str, Enum):
    LINKEDIN = "LinkedIn"
    TWITTER = "X/Twitter"
    BLOG = "Blog"
    INSTAGRAM = "Instagram caption"

class WorkflowStatus(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    RESEARCHING = "RESEARCHING"
    FACT_CHECKING = "FACT_CHECKING"
    WRITING = "WRITING"
    EDITING = "EDITING"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
    FAILED = "FAILED"

class ClaimStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"

class ContentRequest(BaseModel):
    topic: str
    platform: Platform
    audience: str
    tone: str
    posts: int = Field(1, ge=1, le=10)
    length: str = "Medium"
    keywords: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)
    provider: Optional[str] = None
    model: Optional[str] = None

class Source(BaseModel):
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    source_type: str = "web"

class Claim(BaseModel):
    claim: str
    evidence: Optional[str] = None
    source: Optional[Source] = None
    status: ClaimStatus = ClaimStatus.UNSUPPORTED
    confidence: float = 0.0

class ResearchResult(BaseModel):
    claims: List[Claim] = Field(default_factory=list)
    sources: List[Source] = Field(default_factory=list)

class Draft(BaseModel):
    content: str
    platform: Platform
    post_index: int

class EditorFeedback(BaseModel):
    quality_score: float = 0.0
    passed: bool = False
    issues: List[str] = Field(default_factory=list)
    revision_instructions: Optional[str] = None

class AgentMetrics(BaseModel):
    agent: str
    iteration: int
    latency_ms: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float = 0.0
    success: bool = True
    error: Optional[str] = None

class CreateResponse(BaseModel):
    run_id: str
    status: WorkflowStatus

class StatusResponse(BaseModel):
    run_id: str
    status: WorkflowStatus
    current_agent: Optional[str] = None
    revision_count: int
    quality_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

class MetricsResponse(BaseModel):
    run_id: str
    total_latency_ms: int
    total_tokens: int
    total_cost: float
    agent_metrics: List[AgentMetrics]

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
