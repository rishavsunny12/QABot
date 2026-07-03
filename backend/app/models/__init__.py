import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class TeamRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


ROLE_RANK = {
    TeamRole.VIEWER.value: 1,
    TeamRole.MEMBER.value: 2,
    TeamRole.ADMIN.value: 3,
    TeamRole.OWNER.value: 4,
}


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sso_subject: Mapped[str | None] = mapped_column(String(512), unique=True, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    memberships: Mapped[list["TeamMember"]] = relationship(back_populates="user")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    members: Mapped[list["TeamMember"]] = relationship(back_populates="team")
    projects: Mapped[list["Project"]] = relationship(back_populates="team")
    subscription: Mapped["TeamSubscription | None"] = relationship(back_populates="team")
    usage_events: Mapped[list["UsageEvent"]] = relationship(back_populates="team")


class BillingPlan(Base):
    __tablename__ = "billing_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, default=0)
    limits_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    subscriptions: Mapped[list["TeamSubscription"]] = relationship(back_populates="plan")


class TeamSubscription(Base):
    __tablename__ = "team_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), unique=True, index=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("billing_plans.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    team: Mapped["Team"] = relationship(back_populates="subscription")
    plan: Mapped["BillingPlan"] = relationship(back_populates="subscriptions")


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)
    metric: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    team: Mapped["Team"] = relationship(back_populates="usage_events")


class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), default=TeamRole.MEMBER.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    team: Mapped["Team"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    login_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    allowed_domains_json: Mapped[list] = mapped_column(JSON, default=list)
    seed_urls_json: Mapped[list] = mapped_column(JSON, default=list)
    crawl_status: Mapped[str] = mapped_column(String(50), default="idle")
    crawl_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crawl_pages_count: Mapped[int] = mapped_column(Integer, default=0)
    crawl_elements_count: Mapped[int] = mapped_column(Integer, default=0)
    parallel_workers: Mapped[int] = mapped_column(Integer, default=1)
    execution_mode: Mapped[str] = mapped_column(String(20), default="local")
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"), index=True, nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    credentials: Mapped["ProjectCredential | None"] = relationship(back_populates="project")
    team: Mapped["Team | None"] = relationship(back_populates="projects")
    pages: Mapped[list["Page"]] = relationship(back_populates="project")
    flows: Mapped[list["Flow"]] = relationship(back_populates="project")
    generated_tests: Mapped[list["GeneratedTest"]] = relationship(back_populates="project")
    test_runs: Mapped[list["TestRun"]] = relationship(back_populates="project")
    schedules: Mapped[list["TestSchedule"]] = relationship(back_populates="project")
    visual_baselines: Mapped[list["VisualBaseline"]] = relationship(back_populates="project")
    visual_runs: Mapped[list["VisualComparisonRun"]] = relationship(back_populates="project")


class VisualBaseline(Base):
    __tablename__ = "visual_baselines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    page_id: Mapped[str | None] = mapped_column(ForeignKey("pages.id"), nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    screenshot_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="visual_baselines")


class VisualComparisonRun(Base):
    __tablename__ = "visual_comparison_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="running")
    threshold_percent: Mapped[float] = mapped_column(Float, default=1.0)
    pass_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="visual_runs")
    results: Mapped[list["VisualComparisonResult"]] = relationship(back_populates="run")


class VisualComparisonResult(Base):
    __tablename__ = "visual_comparison_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("visual_comparison_runs.id"), index=True)
    baseline_id: Mapped[str] = mapped_column(ForeignKey("visual_baselines.id"), index=True)
    page_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    baseline_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    current_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    diff_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    diff_percent: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    run: Mapped["VisualComparisonRun"] = relationship(back_populates="results")


class TestSchedule(Base):
    __tablename__ = "test_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    test_ids_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    project: Mapped["Project"] = relationship(back_populates="schedules")


class ProjectCredential(Base):
    __tablename__ = "project_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    auth_strategy: Mapped[str] = mapped_column(String(50), default="form")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="credentials")


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    dom_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="pages")
    elements: Mapped[list["Element"]] = relationship(back_populates="page")


class Element(Base):
    __tablename__ = "elements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), index=True)
    element_type: Mapped[str] = mapped_column(String(50), nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    aria_label: Mapped[str | None] = mapped_column(String(512), nullable=True)
    selector_primary: Mapped[str] = mapped_column(String(1024), nullable=False)
    selector_fallbacks_json: Mapped[list] = mapped_column(JSON, default=list)
    dom_signature_json: Mapped[dict] = mapped_column(JSON, default=dict)

    page: Mapped["Page"] = relationship(back_populates="elements")


class PageTransition(Base):
    __tablename__ = "page_transitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    from_page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), index=True)
    to_page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), index=True)
    trigger_element_id: Mapped[str | None] = mapped_column(ForeignKey("elements.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(50), default="click")


class Flow(Base):
    __tablename__ = "flows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)
    requires_auth: Mapped[bool] = mapped_column(Boolean, default=False)
    destructive: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="flows")
    steps: Mapped[list["FlowStep"]] = relationship(back_populates="flow", order_by="FlowStep.step_order")


class FlowStep(Base):
    __tablename__ = "flow_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    flow_id: Mapped[str] = mapped_column(ForeignKey("flows.id"), index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_element_id: Mapped[str | None] = mapped_column(ForeignKey("elements.id"), nullable=True)
    expected_result_json: Mapped[dict] = mapped_column(JSON, default=dict)

    flow: Mapped["Flow"] = relationship(back_populates="steps")


class GeneratedTestStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"
    OUTDATED = "outdated"


class GeneratedTest(Base):
    __tablename__ = "generated_tests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    flow_id: Mapped[str | None] = mapped_column(ForeignKey("flows.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default=GeneratedTestStatus.DRAFT.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="generated_tests")
    flow: Mapped["Flow | None"] = relationship()
    results: Mapped[list["TestRunResult"]] = relationship(back_populates="generated_test")
    healing_suggestions: Mapped[list["HealingSuggestion"]] = relationship(back_populates="generated_test")


class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    run_type: Mapped[str] = mapped_column(String(50), default="manual")
    status: Mapped[str] = mapped_column(String(50), default="queued")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(100), default="user")
    parallel_workers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="test_runs")
    results: Mapped[list["TestRunResult"]] = relationship(back_populates="test_run")


class TestRunResult(Base):
    __tablename__ = "test_run_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    test_run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.id"), index=True)
    generated_test_id: Mapped[str] = mapped_column(ForeignKey("generated_tests.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    trace_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    video_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    test_run: Mapped["TestRun"] = relationship(back_populates="results")
    generated_test: Mapped["GeneratedTest"] = relationship(back_populates="results")
    healing_suggestions: Mapped[list["HealingSuggestion"]] = relationship(back_populates="test_run_result")


class HealingSuggestion(Base):
    __tablename__ = "healing_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    generated_test_id: Mapped[str] = mapped_column(ForeignKey("generated_tests.id"), index=True)
    test_run_result_id: Mapped[str | None] = mapped_column(
        ForeignKey("test_run_results.id"), nullable=True
    )
    failed_selector: Mapped[str] = mapped_column(String(1024), nullable=False)
    suggested_selector: Mapped[str] = mapped_column(String(1024), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    generated_test: Mapped["GeneratedTest"] = relationship(back_populates="healing_suggestions")
    test_run_result: Mapped["TestRunResult | None"] = relationship(back_populates="healing_suggestions")
