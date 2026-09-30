from sqlalchemy import Column, String, Float, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from ..database import Base

class RunRecord(Base):
    __tablename__ = "runs"
    run_id = Column(String, primary_key=True, index=True)
    status = Column(String, index=True)
    request = Column(Text)
    final_content = Column(Text)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    total_latency_ms = Column(Integer, default=0)
    revision_count = Column(Integer, default=0)
    quality_score = Column(Float)
    errors = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    agent_metrics = relationship("AgentMetricRecord", back_populates="run", cascade="all, delete-orphan")
    sources = relationship("SourceRecord", back_populates="run", cascade="all, delete-orphan")
    llm_provider = Column(String, index=True, nullable=True)
    llm_model = Column(String, nullable=True)

class AgentMetricRecord(Base):
    __tablename__ = "agent_metrics"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("runs.run_id"), nullable=False)
    agent = Column(String, index=True)
    iteration = Column(Integer)
    latency_ms = Column(Integer)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    total_tokens = Column(Integer)
    estimated_cost = Column(Float, default=0.0)
    success = Column(Integer, default=1)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    run = relationship("RunRecord", back_populates="agent_metrics")

class SourceRecord(Base):
    __tablename__ = "sources"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("runs.run_id"), nullable=False)
    url = Column(String)
    title = Column(String)
    source_type = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    run = relationship("RunRecord", back_populates="sources")
