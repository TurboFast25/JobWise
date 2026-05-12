"""add category to recipes and email to users

Revision ID: 003
Revises: 002
Create Date: 2026-05-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("category", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_user_email", "users", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_user_email", "users", type_="unique")
    op.drop_column("users", "email")
    op.drop_column("recipes", "category")
