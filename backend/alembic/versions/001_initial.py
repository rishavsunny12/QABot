"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-03
"""

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("base_url", sa.String(2048), nullable=False),
        sa.Column("login_url", sa.String(2048), nullable=True),
        sa.Column("allowed_domains_json", sa.JSON(), nullable=True),
        sa.Column("seed_urls_json", sa.JSON(), nullable=True),
        sa.Column("crawl_status", sa.String(50), server_default="idle"),
        sa.Column("crawl_job_id", sa.String(255), nullable=True),
        sa.Column("crawl_pages_count", sa.Integer(), server_default="0"),
        sa.Column("crawl_elements_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "project_credentials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), unique=True),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("encrypted_password", sa.Text(), nullable=False),
        sa.Column("auth_strategy", sa.String(50), server_default="form"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_project_credentials_project_id", "project_credentials", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_project_credentials_project_id", "project_credentials")
    op.drop_table("project_credentials")
    op.drop_table("projects")
