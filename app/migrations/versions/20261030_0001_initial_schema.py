from alembic import op
import sqlalchemy as sa

from app.database import Base
from app import models

revision = "20261030_0001"
down_revision = None
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    if "departments" in existing_tables and "parent_id" not in _column_names("departments"):
        with op.batch_alter_table("departments") as batch:
            batch.add_column(
                sa.Column(
                    "parent_id",
                    sa.Integer(),
                    sa.ForeignKey(
                        "departments.id",
                        name="fk_departments_parent_id",
                        ondelete="RESTRICT",
                    ),
                    nullable=True,
                )
            )

    if "teachers" in existing_tables:
        teacher_columns = _column_names("teachers")
        if "created_at" not in teacher_columns:
            op.add_column(
                "teachers",
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                ),
            )
            op.execute(
                "UPDATE teachers SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
            )
        if "updated_at" not in teacher_columns:
            op.add_column(
                "teachers",
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                ),
            )
            op.execute(
                "UPDATE teachers SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"
            )

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    raise NotImplementedError("This data-preserving initial migration is not reversible.")
