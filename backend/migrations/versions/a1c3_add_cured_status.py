"""add cured loan status

Revision ID: a1c3add0cured
Revises: f821bdd591da
"""
from alembic import op

revision = "a1c3add0cured"
down_revision = "f821bdd591da"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE loanstatus ADD VALUE IF NOT EXISTS 'cured'")


def downgrade() -> None:
    # Postgres cannot drop an enum value; left in place.
    pass
