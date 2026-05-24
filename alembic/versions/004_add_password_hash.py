"""add password_hash to users for JWT authentication

Revision ID: 004
Revises: 003
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# bcrypt hash of "password123" — lets seeded users log in locally after migration
SEED_PASSWORD_HASH = (
    "$2b$12$r98DKI5VCzrZEDycRWcLkO/d8lTrf3FykdvlTRbWzL3FmCH9CPewK"
)


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.execute(
        sa.text("UPDATE users SET password_hash = :hash WHERE password_hash IS NULL").bindparams(
            hash=SEED_PASSWORD_HASH
        )
    )
    op.alter_column("users", "password_hash", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "password_hash")
