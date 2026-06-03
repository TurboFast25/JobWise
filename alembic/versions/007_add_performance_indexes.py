"""add performance indexes for feed and ingredient lookups

Revision ID: 007
Revises: 006
Create Date: 2026-06-03

"""
from typing import Sequence, Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_recipes_category
        ON recipes(category)
        WHERE is_canonical = true
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_reviews_recipe_covering
        ON reviews(recipe_id)
        INCLUDE (user_id, raw_score, review_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id
        ON recipe_ingredients(recipe_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_recipes_category")
    op.execute("DROP INDEX IF EXISTS idx_reviews_recipe_covering")
    op.execute("DROP INDEX IF EXISTS idx_recipe_ingredients_recipe_id")