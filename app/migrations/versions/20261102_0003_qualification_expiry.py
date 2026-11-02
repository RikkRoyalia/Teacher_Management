from alembic import op
import sqlalchemy as sa

revision = "20261102_0003"
down_revision = "20261030_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("qualifications")
    }
    if "expires_on" not in columns:
        with op.batch_alter_table("qualifications") as batch_op:
            batch_op.add_column(sa.Column("expires_on", sa.Date(), nullable=True))
            batch_op.create_check_constraint(
                "ck_qualification_expiry_date",
                "expires_on IS NULL OR issued_on IS NULL OR expires_on >= issued_on",
            )


def downgrade() -> None:
    raise NotImplementedError("This data-preserving migration is not reversible.")
