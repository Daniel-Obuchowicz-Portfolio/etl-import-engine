"""Initial ETL schema."""

import sqlalchemy as sa

from alembic import op

revision = "20260824_0001"
down_revision = None
branch_labels = None
depends_on = None

source_type = sa.Enum("csv", "json", "api", name="sourcetype")
import_status = sa.Enum(
    "pending", "processing", "completed", "completed_with_errors", "failed", name="importstatus"
)
duplicate_strategy = sa.Enum("skip", "update", "error", name="duplicatestrategy")


def upgrade() -> None:
    op.create_table(
        "mapping_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
        sa.Column("mapping", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(100)),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("tax_id", sa.String(50), unique=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_companies_external_id", "companies", ["external_id"], unique=True)
    op.create_index("ix_companies_name", "companies", ["name"])
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(100)),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(32)),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_customers_email", "customers", ["email"], unique=True)
    op.create_index("ix_customers_external_id", "customers", ["external_id"], unique=True)
    op.create_index("ix_customers_phone", "customers", ["phone"], unique=True)
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("filename", sa.String(255)),
        sa.Column("status", import_status, nullable=False),
        sa.Column(
            "mapping_profile_id",
            sa.Integer(),
            sa.ForeignKey("mapping_profiles.id", ondelete="SET NULL"),
        ),
        sa.Column("duplicate_strategy", duplicate_strategy, nullable=False),
        sa.Column("total_records", sa.Integer(), server_default="0", nullable=False),
        sa.Column("processed_records", sa.Integer(), server_default="0", nullable=False),
        sa.Column("successful_records", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_records", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_records", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_records", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_import_jobs_status_created", "import_jobs", ["status", "created_at"])
    op.create_index("ix_import_jobs_source_created", "import_jobs", ["source_type", "created_at"])
    op.create_table(
        "import_errors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "import_job_id",
            sa.Integer(),
            sa.ForeignKey("import_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("field", sa.String(100)),
        sa.Column("raw_value", sa.Text()),
        sa.Column("error_code", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("raw_record", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_import_errors_job_row", "import_errors", ["import_job_id", "row_number"])


def downgrade() -> None:
    op.drop_table("import_errors")
    op.drop_table("import_jobs")
    op.drop_table("customers")
    op.drop_table("companies")
    op.drop_table("mapping_profiles")
    duplicate_strategy.drop(op.get_bind(), checkfirst=True)
    import_status.drop(op.get_bind(), checkfirst=True)
    source_type.drop(op.get_bind(), checkfirst=True)
