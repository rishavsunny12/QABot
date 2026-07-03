from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str
    base_url: str
    login_url: str | None = None
    username: str | None = None
    password: str | None = None
    auth_strategy: str = "form"
    allowed_domains: list[str] = Field(default_factory=list)
    seed_urls: list[str] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    login_url: str | None = None
    username: str | None = None
    password: str | None = None
    auth_strategy: str | None = None
    allowed_domains: list[str] | None = None
    seed_urls: list[str] | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    base_url: str
    login_url: str | None
    allowed_domains: list[str]
    seed_urls: list[str]
    crawl_status: str
    crawl_pages_count: int
    crawl_elements_count: int
    has_credentials: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CrawlStatusResponse(BaseModel):
    status: str
    job_id: str | None
    pages_count: int
    elements_count: int
    message: str | None = None


class ElementResponse(BaseModel):
    id: str
    page_id: str
    element_type: str
    text_content: str | None
    aria_label: str | None
    selector_primary: str
    selector_fallbacks: list[str]

    model_config = {"from_attributes": True}


class PageResponse(BaseModel):
    id: str
    project_id: str
    url: str
    title: str | None
    screenshot_path: str | None
    discovered_at: datetime
    elements: list[ElementResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class FlowStepResponse(BaseModel):
    id: str
    step_order: int
    action_type: str
    target_element_id: str | None
    expected_result: dict[str, Any]

    model_config = {"from_attributes": True}


class FlowResponse(BaseModel):
    id: str
    project_id: str
    name: str
    risk_level: str
    confidence_score: float
    requires_auth: bool
    destructive: bool
    steps: list[FlowStepResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class GeneratedTestResponse(BaseModel):
    id: str
    project_id: str
    flow_id: str | None
    name: str
    file_path: str
    version: int
    status: str
    created_at: datetime
    flow_name: str | None = None

    model_config = {"from_attributes": True}


class TestRunResponse(BaseModel):
    id: str
    project_id: str
    run_type: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    triggered_by: str
    pass_count: int = 0
    fail_count: int = 0
    total_count: int = 0

    model_config = {"from_attributes": True}


class TestRunResultResponse(BaseModel):
    id: str
    test_run_id: str
    generated_test_id: str
    test_name: str | None = None
    status: str
    duration_ms: int | None
    failure_category: str | None
    error_message: str | None
    screenshot_path: str | None
    trace_path: str | None
    video_path: str | None
    ai_summary: str | None

    model_config = {"from_attributes": True}


class HealingSuggestionResponse(BaseModel):
    id: str
    generated_test_id: str
    failed_selector: str
    suggested_selector: str
    confidence_score: float
    rationale: str | None
    approved: bool | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RunTestsRequest(BaseModel):
    test_ids: list[str] | None = None


class GenerateTestsRequest(BaseModel):
    flow_ids: list[str] | None = None


class GraphNode(BaseModel):
    id: str
    label: str
    url: str


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None


class FlowGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    flows: list[FlowResponse]
