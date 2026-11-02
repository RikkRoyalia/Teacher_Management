from alembic import op
import sqlalchemy as sa


revision = "20261102_0004"
down_revision = "20261102_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")
    }
    if "teacher_id" not in user_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_constraint("ck_user_role", type_="check")
            batch_op.add_column(sa.Column("teacher_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_users_teacher_id_teachers",
                "teachers",
                ["teacher_id"],
                ["id"],
                ondelete="RESTRICT",
            )
            batch_op.create_unique_constraint("uq_user_teacher", ["teacher_id"])
            batch_op.create_check_constraint(
                "ck_user_role",
                "role IN ('admin', 'hr', 'manager', 'lecturer')",
            )
            batch_op.create_check_constraint(
                "ck_user_teacher_link",
                "(role = 'lecturer' AND teacher_id IS NOT NULL) "
                "OR (role != 'lecturer' AND teacher_id IS NULL)",
            )

    document_columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("evidence_documents")
    }
    if "review_status" not in document_columns:
        with op.batch_alter_table("evidence_documents") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "review_status",
                    sa.String(20),
                    nullable=False,
                    server_default="approved",
                )
            )
            batch_op.add_column(sa.Column("review_reason", sa.String(1000)))
            batch_op.add_column(sa.Column("reviewed_by", sa.Integer()))
            batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True)))
            batch_op.create_foreign_key(
                "fk_evidence_documents_reviewed_by_users",
                "users",
                ["reviewed_by"],
                ["id"],
                ondelete="RESTRICT",
            )
            batch_op.create_check_constraint(
                "ck_evidence_document_review_status",
                "review_status IN ('pending', 'approved', 'rejected')",
            )


def downgrade() -> None:
    raise NotImplementedError("This data-preserving migration is not reversible.")
