from alembic import op
import sqlalchemy as sa


revision = "20261109_0006"
down_revision = "20261103_0005"
branch_labels = None
depends_on = None


def _create_index_if_missing(name: str, table_name: str, columns: list[str]) -> None:
    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
    if name not in {index["name"] for index in indexes}:
        op.create_index(name, table_name, columns)


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "manager_department_assignments" not in existing_tables:
        op.create_table(
            "manager_department_assignments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("manager_id", sa.Integer(), nullable=False),
            sa.Column("department_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["manager_id"], ["users.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["department_id"], ["departments.id"], ondelete="RESTRICT"
            ),
            sa.UniqueConstraint(
                "manager_id",
                "department_id",
                name="uq_manager_department_assignment",
            ),
        )
    if "notifications" not in existing_tables:
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("event_key", sa.String(length=160), nullable=False),
            sa.Column("level", sa.String(length=20), nullable=False),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("target_view", sa.String(length=40), nullable=False),
            sa.Column("target_id", sa.String(length=80), nullable=True),
            sa.Column(
                "is_read",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "user_id", "event_key", name="uq_notification_user_event"
            ),
        )

    _create_index_if_missing(
        "ix_manager_department_assignments_manager_id",
        "manager_department_assignments",
        ["manager_id"],
    )
    _create_index_if_missing(
        "ix_manager_department_assignments_department_id",
        "manager_department_assignments",
        ["department_id"],
    )
    _create_index_if_missing(
        "ix_notifications_user_id", "notifications", ["user_id"]
    )
    _create_index_if_missing(
        "ix_notifications_user_created_at",
        "notifications",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    raise NotImplementedError("This data-preserving migration is not reversible.")
