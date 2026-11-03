from alembic import op


revision = "20261103_0005"
down_revision = "20261102_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("evidence_documents") as batch_op:
        batch_op.drop_constraint(
            "ck_evidence_document_review_status",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_evidence_document_review_status",
            "review_status IN ('pending', 'approved', 'rejected', 'withdrawn')",
        )


def downgrade() -> None:
    raise NotImplementedError("This data-preserving migration is not reversible.")
