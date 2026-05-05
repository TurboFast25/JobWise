"""create initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-04

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(255), nullable=False, unique=True),
        sa.Column("trust_authority", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "recipes",
        sa.Column("recipe_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("is_canonical", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("canonical_id", sa.Integer(), sa.ForeignKey("recipes.recipe_id"), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "ingredients",
        sa.Column("ingredient_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "recipe_id",
            sa.Integer(),
            sa.ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.String(255), nullable=True),
    )

    op.create_table(
        "reviews",
        sa.Column("review_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "recipe_id",
            sa.Integer(),
            sa.ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("raw_score", sa.Float(), nullable=False),
        sa.Column("z_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "recipe_id", name="uq_user_recipe_review"),
    )

    op.create_table(
        "follows",
        sa.Column("follow_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "follower_id",
            sa.Integer(),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "followee_id",
            sa.Integer(),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trust_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("follower_id", "followee_id", name="uq_follow"),
    )

    op.create_table(
        "cookbook_entries",
        sa.Column("entry_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "recipe_id",
            sa.Integer(),
            sa.ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("personal_rank", sa.Integer(), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "recipe_id", name="uq_cookbook_entry"),
    )


def downgrade() -> None:
    op.drop_table("cookbook_entries")
    op.drop_table("follows")
    op.drop_table("reviews")
    op.drop_table("ingredients")
    op.drop_table("recipes")
    op.drop_table("users")
