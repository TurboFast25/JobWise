from sqlalchemy import text
from sqlalchemy.orm import Session


def link_recipe_ingredients(db: Session, recipe_id: int, ingredient_names: list[str]) -> None:
    for name in ingredient_names:
        trimmed = name.strip()
        if not trimmed:
            continue

        catalog = db.execute(
            text(
                """
                SELECT ingredient_id
                FROM ingredient_catalog
                WHERE lower(trim(name)) = lower(trim(:name))
                """
            ),
            {"name": trimmed},
        ).fetchone()

        if catalog is None:
            catalog = db.execute(
                text(
                    """
                    INSERT INTO ingredient_catalog (name)
                    VALUES (:name)
                    RETURNING ingredient_id
                    """
                ),
                {"name": trimmed},
            ).fetchone()

        if catalog is None:
            continue

        db.execute(
            text(
                """
                INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity)
                VALUES (:rid, :iid, '')
                ON CONFLICT (recipe_id, ingredient_id) DO NOTHING
                """
            ),
            {"rid": recipe_id, "iid": catalog.ingredient_id},
        )
