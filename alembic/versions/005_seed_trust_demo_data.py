"""seed follows and reviews so example flows show non-zero trust scores

Revision ID: 005
Revises: 004
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE recipes SET category = 'Italian' WHERE recipe_id = 2")

    op.execute("""
        INSERT INTO follows (follower_id, followee_id, trust_weight)
        VALUES (2, 3, 1.0)
        ON CONFLICT ON CONSTRAINT uq_follow DO NOTHING
    """)

    op.execute("""
        INSERT INTO reviews (user_id, recipe_id, raw_score, z_score, comment)
        VALUES
            (3, 1, 6.0, 0.0, 'Solid weeknight ramen'),
            (3, 2, 9.5, 1.2, 'Best miso carbonara I have made')
        ON CONFLICT ON CONSTRAINT uq_user_recipe_review DO NOTHING
    """)

    op.execute("""
        UPDATE users
        SET trust_authority = COALESCE(
            (SELECT AVG(ABS(z_score)) FROM reviews WHERE user_id = 3),
            0.0
        )
        WHERE user_id = 3
    """)


def downgrade() -> None:
    op.execute("DELETE FROM reviews WHERE user_id = 3 AND recipe_id IN (1, 2)")
    op.execute("DELETE FROM follows WHERE follower_id = 2 AND followee_id = 3")
    op.execute("UPDATE recipes SET category = NULL WHERE recipe_id = 2")
    op.execute("UPDATE users SET trust_authority = 0.0 WHERE user_id = 3")
