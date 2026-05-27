"""schema and integrity improvements from design review

Revision ID: 006
Revises: 005
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- recipe_merges: confidence belongs on dedup relationship, not recipe row ---
    op.create_table(
        "recipe_merges",
        sa.Column("merge_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "canonical_recipe_id",
            sa.Integer(),
            sa.ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_recipe_id",
            sa.Integer(),
            sa.ForeignKey("recipes.recipe_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("merged_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- author + timestamps ---
    op.add_column(
        "recipes",
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "recipes",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "follows",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "reviews",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "cookbook_entries",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Canonical invariant: no self-reference; canonical rows should not point elsewhere
    op.create_check_constraint(
        "ck_recipes_canonical_not_self",
        "recipes",
        "canonical_id IS NULL OR canonical_id != recipe_id",
    )
    op.create_check_constraint(
        "ck_recipes_canonical_row_has_no_pointer",
        "recipes",
        "is_canonical = false OR canonical_id IS NULL",
    )

    # Cookbook ranks: normalize then enforce uniqueness per user
    op.execute(
        """
        WITH ranked AS (
            SELECT entry_id,
                   ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY personal_rank, entry_id) AS new_rank
            FROM cookbook_entries
        )
        UPDATE cookbook_entries ce
        SET personal_rank = ranked.new_rank
        FROM ranked
        WHERE ce.entry_id = ranked.entry_id
        """
    )
    op.create_unique_constraint("uq_cookbook_user_rank", "cookbook_entries", ["user_id", "personal_rank"])

    # --- ingredients: many-to-many via catalog + join table ---
    op.create_table(
        "ingredient_catalog",
        sa.Column("ingredient_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_ingredient_catalog_name_lower "
        "ON ingredient_catalog (lower(trim(name)))"
    )

    op.create_table(
        "recipe_ingredients",
        sa.Column(
            "recipe_id",
            sa.Integer(),
            sa.ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "ingredient_id",
            sa.Integer(),
            sa.ForeignKey("ingredient_catalog.ingredient_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("quantity", sa.String(255), nullable=True),
    )

    op.execute(
        """
        INSERT INTO ingredient_catalog (name)
        SELECT DISTINCT ON (lower(trim(name)))
               trim(name)
        FROM ingredients
        WHERE trim(name) <> ''
        ORDER BY lower(trim(name)), trim(name)
        """
    )
    op.execute(
        """
        INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity)
        SELECT i.recipe_id, c.ingredient_id, i.quantity
        FROM ingredients i
        JOIN ingredient_catalog c ON lower(trim(c.name)) = lower(trim(i.name))
        """
    )
    op.drop_table("ingredients")

    # Drop denormalized columns (computed at read time in API)
    op.drop_column("recipes", "confidence")
    op.drop_column("users", "trust_authority")
    op.drop_column("follows", "trust_weight")
    op.drop_column("reviews", "z_score")


def downgrade() -> None:
    op.add_column("reviews", sa.Column("z_score", sa.Float(), server_default="0.0", nullable=False))
    op.add_column("follows", sa.Column("trust_weight", sa.Float(), server_default="1.0", nullable=False))
    op.add_column("users", sa.Column("trust_authority", sa.Float(), server_default="0.0", nullable=False))
    op.add_column("recipes", sa.Column("confidence", sa.Float(), nullable=True))

    op.create_table(
        "ingredients",
        sa.Column("ingredient_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("recipes.recipe_id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.String(255), nullable=True),
    )
    op.execute(
        """
        INSERT INTO ingredients (recipe_id, name, quantity)
        SELECT ri.recipe_id, c.name, ri.quantity
        FROM recipe_ingredients ri
        JOIN ingredient_catalog c ON c.ingredient_id = ri.ingredient_id
        """
    )
    op.execute("DROP INDEX IF EXISTS uq_ingredient_catalog_name_lower")
    op.drop_table("recipe_ingredients")
    op.drop_table("ingredient_catalog")

    op.drop_constraint("uq_cookbook_user_rank", "cookbook_entries", type_="unique")
    op.drop_constraint("ck_recipes_canonical_row_has_no_pointer", "recipes", type_="check")
    op.drop_constraint("ck_recipes_canonical_not_self", "recipes", type_="check")

    op.drop_column("cookbook_entries", "updated_at")
    op.drop_column("reviews", "updated_at")
    op.drop_column("follows", "updated_at")
    op.drop_column("users", "updated_at")
    op.drop_column("recipes", "updated_at")
    op.drop_column("recipes", "author_id")
    op.drop_table("recipe_merges")
