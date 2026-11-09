from alembic import op
import sqlalchemy as sa


revision = "20261109_0007"
down_revision = "20261109_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {
        column["name"]
        for column in inspector.get_columns("notifications")
    }
    has_manager_faculty_foreign_key = any(
        foreign_key["constrained_columns"] == ["manager_faculty_id"]
        and foreign_key["referred_table"] == "departments"
        for foreign_key in inspector.get_foreign_keys("notifications")
    )
    if "manager_faculty_id" not in columns or (
        not has_manager_faculty_foreign_key
    ):
        with op.batch_alter_table("notifications") as batch_op:
            if "manager_faculty_id" not in columns:
                batch_op.add_column(
                    sa.Column("manager_faculty_id", sa.Integer(), nullable=True)
                )
            if not has_manager_faculty_foreign_key:
                batch_op.create_foreign_key(
                    "fk_notifications_manager_faculty_id_departments",
                    "departments",
                    ["manager_faculty_id"],
                    ["id"],
                    ondelete="SET NULL",
                )

    indexes = {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes("notifications")
    }
    if "ix_notifications_user_manager_faculty" not in indexes:
        op.create_index(
            "ix_notifications_user_manager_faculty",
            "notifications",
            ["user_id", "manager_faculty_id"],
        )


def downgrade() -> None:
    raise NotImplementedError("This data-preserving migration is not reversible.")
