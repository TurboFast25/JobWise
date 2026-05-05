"""seed initial data

Revision ID: 002
Revises: 001
Create Date: 2026-05-04

"""
from typing import Sequence, Union
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO users (username, trust_authority) VALUES
        ('diego_cooks', 0.0),
        ('jennifer_eats', 0.0),
        ('louis_chef', 0.0)
    """)

    op.execute("""
        INSERT INTO recipes (title, instructions, is_canonical) VALUES
        ('Spicy Ramen',
         'Boil broth with miso paste and chili paste for 10 minutes. Cook ramen noodles separately. Soft boil eggs for 6 minutes. Combine noodles and broth in a bowl. Top with egg sliced in half and nori sheets.',
         true),
        ('Miso Carbonara',
         'Cook spaghetti until al dente, reserve 1 cup pasta water. Whisk eggs and parmesan together. Fry bacon until crispy. Mix miso paste into egg mixture. Toss hot pasta with bacon, then egg mixture off heat, adding pasta water to loosen.',
         true),
        ('Classic Tomato Sauce',
         'Sauté minced garlic in olive oil over medium heat for 2 minutes. Add crushed tomatoes and stir. Simmer uncovered for 20 minutes. Season with salt, pepper, and fresh basil.',
         true)
    """)

    op.execute("""
        INSERT INTO ingredients (recipe_id, name, quantity) VALUES
        (1, 'ramen noodles', '2 servings'),
        (1, 'miso paste', '2 tbsp'),
        (1, 'chili paste', '1 tbsp'),
        (1, 'soft boiled egg', '2'),
        (1, 'nori', '2 sheets'),
        (1, 'chicken broth', '4 cups'),
        (2, 'spaghetti', '200g'),
        (2, 'eggs', '3'),
        (2, 'parmesan', '50g'),
        (2, 'miso paste', '1 tbsp'),
        (2, 'bacon', '100g'),
        (3, 'crushed tomatoes', '1 can'),
        (3, 'garlic', '4 cloves'),
        (3, 'olive oil', '3 tbsp'),
        (3, 'fresh basil', '10 leaves')
    """)


def downgrade() -> None:
    op.execute("DELETE FROM ingredients WHERE recipe_id IN (1, 2, 3)")
    op.execute("DELETE FROM recipes WHERE recipe_id IN (1, 2, 3)")
    op.execute("DELETE FROM users WHERE username IN ('diego_cooks', 'jennifer_eats', 'louis_chef')")
