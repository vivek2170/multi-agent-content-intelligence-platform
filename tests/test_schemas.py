import pytest
from backend.app.models.schemas import ContentRequest, Platform, WorkflowStatus, ClaimStatus

def test_content_request_defaults():
    req = ContentRequest(topic="AI", platform=Platform.LINKEDIN, audience="engineers", tone="Professional")
    assert req.posts == 1
    assert req.length == "Medium"
    assert req.keywords == []

def test_workflow_status_values():
    assert WorkflowStatus.CREATED == "CREATED"
    assert WorkflowStatus.APPROVED == "APPROVED"

def test_claim_status_values():
    assert ClaimStatus.VERIFIED == "VERIFIED"
    assert ClaimStatus.CONTRADICTED == "CONTRADICTED"
