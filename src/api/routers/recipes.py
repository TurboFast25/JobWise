from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from src.database import get_db

router = APIRouter(tags=["recipes"])


class IngestRequest(BaseModel):
    title: str
    ingredients: List[str]
    category: Optional[str] = None


@router.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.execute(
        text("SELECT recipe_id, title, instructions, is_canonical, category FROM recipes WHERE recipe_id = :id"),
        {"id": recipe_id}
    ).fetchone()

    if not recipe:
        raise HTTPException(404, "Recipe not found")

    ingredients = db.execute(
        text("SELECT name, quantity FROM ingredients WHERE recipe_id = :id ORDER BY ingredient_id"),
        {"id": recipe_id}
    ).fetchall()

    return {
        "recipe_id": recipe.recipe_id,
        "title": recipe.title,
        "category": recipe.category,
        "ingredients": [f"{i.name} - {i.quantity}" for i in ingredients],
        "instructions": [s.strip() for s in recipe.instructions.split(".") if s.strip()] if recipe.instructions else [],
        "is_canonical": recipe.is_canonical,
    }

@router.get("/recipes/{recipe_id}/similar")
def get_similar_recipes(recipe_id: int, limit: int = 5, db: Session = Depends(get_db)):
    target = db.execute(
        text("SELECT recipe_id FROM recipes WHERE recipe_id = :id"),
        {"id": recipe_id},
    ).fetchone()

    if not target:
        raise HTTPException(404, "Recipe not found")

    target_ingredients = db.execute(
        text("SELECT LOWER(TRIM(name)) AS name FROM ingredients WHERE recipe_id = :id"),
        {"id": recipe_id},
    ).fetchall()

    target_set = {row.name for row in target_ingredients if row.name}

    if not target_set:
        return []

    candidates = db.execute(
        text("""
            SELECT r.recipe_id, r.title, array_agg(LOWER(TRIM(i.name))) AS ingredients
            FROM recipes r
            JOIN ingredients i ON i.recipe_id = r.recipe_id
            WHERE r.recipe_id != :id
              AND r.is_canonical = true
            GROUP BY r.recipe_id, r.title
        """),
        {"id": recipe_id},
    ).fetchall()

    results = []

    for row in candidates:
        candidate_set = {name for name in row.ingredients if name}
        union = target_set | candidate_set
        similarity = len(target_set & candidate_set) / len(union) if union else 0.0

        if similarity > 0:
            results.append({
                "recipe_id": row.recipe_id,
                "title": row.title,
                "similarity": round(similarity, 4),
                "shared_ingredients": sorted(target_set & candidate_set),
            })

    results.sort(key=lambda r: r["similarity"], reverse=True)
    return results[:limit]

@router.post("/recipes/ingest")
def ingest_recipe(body: IngestRequest, db: Session = Depends(get_db)):
    if not body.title.strip():
        raise HTTPException(422, "Title cannot be empty")

    if not body.ingredients:
        raise HTTPException(422, "Ingredients cannot be empty — please include at least one ingredient")

    incoming = {i.lower().strip() for i in body.ingredients if i.strip()}

    # SERIALIZABLE isolation prevents phantom reads: if two concurrent ingests both
    # scan canonical recipes and find no match, PostgreSQL detects the read/write
    # conflict and aborts one of them, forcing it to retry and see the other's insert.
    db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))

    # Check for duplicates using Jaccard similarity on ingredients
    existing_recipes = db.execute(
        text("""
            SELECT r.recipe_id, array_agg(i.name) AS ingredients
            FROM recipes r
            JOIN ingredients i ON i.recipe_id = r.recipe_id
            WHERE r.is_canonical = true
            GROUP BY r.recipe_id
        """)
    ).fetchall()

    best_match = None
    best_score = 0.0

    for row in existing_recipes:
        existing = {n.lower().strip() for n in row.ingredients}
        union = incoming | existing
        score = len(incoming & existing) / len(union) if union else 0.0
        if score > best_score:
            best_score = score
            best_match = row.recipe_id

    if best_score >= 0.5 and best_match:
        return {"status": "merged", "canonical_id": best_match, "confidence": round(best_score, 3)}

    # No match — create a new recipe
    new_recipe = db.execute(
        text("""
            INSERT INTO recipes (title, instructions, is_canonical, confidence, category)
            VALUES (:title, '', true, 1.0, :category)
            RETURNING recipe_id
        """),
        {"title": body.title.strip(), "category": body.category}
    ).fetchone()

    for name in body.ingredients:
        db.execute(
            text("INSERT INTO ingredients (recipe_id, name, quantity) VALUES (:rid, :name, '')"),
            {"rid": new_recipe.recipe_id, "name": name.strip()}
        )

    db.commit()
    return {"status": "created", "canonical_id": new_recipe.recipe_id, "confidence": 1.0}
