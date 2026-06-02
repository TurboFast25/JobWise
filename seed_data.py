"""
Fake data generator for JobWise performance testing.
Targets a local postgres instance (jobwise_perf).
Uses psycopg COPY for fast bulk loading.

Row distribution (totals to ~1,010,000):
  users            10,000
  recipes          50,000
  ingredients     250,000   (~5 per recipe)
  reviews         500,000   (~50 per user)
  follows         100,000   (~10 per user)
  cookbook_entries 100,000  (~10 per user)
"""

import random
import psycopg
from datetime import datetime, timezone

CONN = "host=localhost dbname=jobwise_perf user=ethanyang"

NUM_USERS     = 10_000
NUM_RECIPES   = 50_000
AVG_INGR      = 5
AVG_REVIEWS   = 50
AVG_FOLLOWS   = 10
AVG_COOKBOOK  = 10

SEED_HASH = "$2b$12$r98DKI5VCzrZEDycRWcLkO/d8lTrf3FykdvlTRbWzL3FmCH9CPewK"

CATEGORIES = [
    "Italian", "Asian", "Mexican", "American", "Mediterranean",
    "Indian", "French", "Japanese", "Thai", "Greek",
    "Chinese", "Spanish", "Korean", "Vietnamese", "Middle Eastern",
]

ADJECTIVES = ["Spicy", "Creamy", "Classic", "Quick", "Hearty",
               "Light", "Crispy", "Smoky", "Fresh", "Tangy"]

NOUNS = ["Pasta", "Soup", "Salad", "Stew", "Curry",
         "Stir Fry", "Casserole", "Bowl", "Tacos", "Risotto"]

INGREDIENT_POOL = [
    "garlic", "onion", "olive oil", "salt", "black pepper", "butter", "flour",
    "eggs", "milk", "sugar", "lemon juice", "tomatoes", "chicken broth",
    "parmesan", "bacon", "soy sauce", "sesame oil", "ginger", "cumin",
    "paprika", "chili flakes", "thyme", "rosemary", "basil", "oregano",
    "rice", "pasta", "chicken", "beef", "pork", "shrimp", "salmon",
    "potatoes", "carrots", "celery", "bell pepper", "mushrooms", "spinach",
    "zucchini", "broccoli", "cauliflower", "corn", "black beans", "chickpeas",
    "lentils", "heavy cream", "sour cream", "yogurt", "mozzarella", "cheddar",
    "feta", "balsamic vinegar", "white wine", "red wine", "honey", "mustard",
    "mayonnaise", "tomato paste", "coconut milk", "fish sauce", "lime juice",
    "cilantro", "parsley", "mint", "turmeric", "curry powder", "coriander",
    "bay leaves", "apple cider vinegar", "worcestershire sauce", "hot sauce",
    "bread crumbs", "cornstarch", "baking powder", "vanilla extract",
    "cinnamon", "nutmeg", "chocolate chips", "cocoa powder", "brown sugar",
    "almonds", "walnuts", "pine nuts", "sesame seeds", "sun-dried tomatoes",
    "capers", "olives", "roasted red peppers", "artichoke hearts",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id       SERIAL PRIMARY KEY,
    username      VARCHAR(255) NOT NULL UNIQUE,
    trust_authority FLOAT NOT NULL DEFAULT 0.0,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    email         VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS recipes (
    recipe_id    SERIAL PRIMARY KEY,
    title        VARCHAR(500) NOT NULL,
    instructions TEXT,
    is_canonical BOOLEAN NOT NULL DEFAULT true,
    canonical_id INTEGER REFERENCES recipes(recipe_id),
    confidence   FLOAT,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    category     VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS ingredients (
    ingredient_id SERIAL PRIMARY KEY,
    recipe_id     INTEGER NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    name          VARCHAR(255) NOT NULL,
    quantity      VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id  SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    recipe_id  INTEGER NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    raw_score  FLOAT NOT NULL,
    z_score    FLOAT NOT NULL DEFAULT 0.0,
    comment    TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_recipe_review UNIQUE(user_id, recipe_id)
);

CREATE TABLE IF NOT EXISTS follows (
    follow_id   SERIAL PRIMARY KEY,
    follower_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    followee_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    trust_weight FLOAT NOT NULL DEFAULT 1.0,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_follow UNIQUE(follower_id, followee_id)
);

CREATE TABLE IF NOT EXISTS cookbook_entries (
    entry_id      SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    recipe_id     INTEGER NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    personal_rank INTEGER,
    added_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_cookbook_entry UNIQUE(user_id, recipe_id)
);
"""


def main() -> None:
    now = datetime.now(timezone.utc)
    rng = random.Random(42)

    with psycopg.connect(CONN) as conn:
        cur = conn.cursor()

        print("Creating schema...")
        cur.execute(SCHEMA)
        conn.commit()

        # Wipe any existing data
        cur.execute(
            "TRUNCATE cookbook_entries, follows, reviews, ingredients, recipes, users "
            "RESTART IDENTITY CASCADE"
        )
        conn.commit()

        # ── Users ────────────────────────────────────────────────────────────
        print(f"Inserting {NUM_USERS:,} users...")
        with cur.copy(
            "COPY users (username, trust_authority, email, password_hash, created_at) FROM STDIN"
        ) as copy:
            for i in range(1, NUM_USERS + 1):
                copy.write_row((
                    f"user_{i:06d}",
                    0.0,
                    f"user_{i:06d}@example.com",
                    SEED_HASH,
                    now,
                ))
        conn.commit()

        # ── Recipes ──────────────────────────────────────────────────────────
        print(f"Inserting {NUM_RECIPES:,} recipes...")
        with cur.copy(
            "COPY recipes (title, instructions, is_canonical, confidence, category, created_at) FROM STDIN"
        ) as copy:
            for i in range(1, NUM_RECIPES + 1):
                cat  = CATEGORIES[i % len(CATEGORIES)]
                adj  = ADJECTIVES[i % len(ADJECTIVES)]
                noun = NOUNS[i % len(NOUNS)]
                copy.write_row((
                    f"{adj} {cat} {noun} #{i}",
                    "Prepare ingredients. Follow standard cooking method. Serve immediately.",
                    True,
                    1.0,
                    cat,
                    now,
                ))
        conn.commit()

        # ── Ingredients (~5 per recipe, 3–8 range) ───────────────────────────
        print("Inserting ingredients...")
        ingr_count = 0
        with cur.copy(
            "COPY ingredients (recipe_id, name, quantity) FROM STDIN"
        ) as copy:
            for recipe_id in range(1, NUM_RECIPES + 1):
                n = rng.randint(3, 8)
                for ing in rng.sample(INGREDIENT_POOL, n):
                    copy.write_row((recipe_id, ing, "1 unit"))
                    ingr_count += 1
        conn.commit()
        print(f"  {ingr_count:,} ingredient rows")

        # ── Reviews (50 per user, unique per user+recipe) ────────────────────
        print(f"Inserting ~{NUM_USERS * AVG_REVIEWS:,} reviews...")
        review_count = 0
        with cur.copy(
            "COPY reviews (user_id, recipe_id, raw_score, z_score, created_at) FROM STDIN"
        ) as copy:
            for user_id in range(1, NUM_USERS + 1):
                for recipe_id in rng.sample(range(1, NUM_RECIPES + 1), AVG_REVIEWS):
                    raw = round(rng.uniform(1.0, 10.0), 1)
                    copy.write_row((user_id, recipe_id, raw, 0.0, now))
                    review_count += 1
        conn.commit()
        print(f"  {review_count:,} review rows")

        # ── Follows (10 per user, unique pairs, no self-follows) ─────────────
        print(f"Inserting ~{NUM_USERS * AVG_FOLLOWS:,} follows...")
        follows_set: set[tuple[int, int]] = set()
        with cur.copy(
            "COPY follows (follower_id, followee_id, trust_weight, created_at) FROM STDIN"
        ) as copy:
            for follower_id in range(1, NUM_USERS + 1):
                added = 0
                candidates = rng.sample(range(1, NUM_USERS + 1), min(AVG_FOLLOWS * 3, NUM_USERS))
                for followee_id in candidates:
                    if added >= AVG_FOLLOWS:
                        break
                    if followee_id == follower_id:
                        continue
                    if (follower_id, followee_id) in follows_set:
                        continue
                    follows_set.add((follower_id, followee_id))
                    copy.write_row((follower_id, followee_id, 1.0, now))
                    added += 1
        conn.commit()
        print(f"  {len(follows_set):,} follow rows")

        # ── Cookbook entries (10 per user, unique per user+recipe) ───────────
        print(f"Inserting ~{NUM_USERS * AVG_COOKBOOK:,} cookbook entries...")
        cb_count = 0
        with cur.copy(
            "COPY cookbook_entries (user_id, recipe_id, personal_rank, added_at) FROM STDIN"
        ) as copy:
            for user_id in range(1, NUM_USERS + 1):
                for rank, recipe_id in enumerate(
                    rng.sample(range(1, NUM_RECIPES + 1), AVG_COOKBOOK), start=1
                ):
                    copy.write_row((user_id, recipe_id, rank, now))
                    cb_count += 1
        conn.commit()
        print(f"  {cb_count:,} cookbook rows")

        # ── Summary ──────────────────────────────────────────────────────────
        print("\n── Row counts ───────────────────────────────")
        total = 0
        for table in ["users", "recipes", "ingredients", "reviews", "follows", "cookbook_entries"]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            n = cur.fetchone()[0]
            print(f"  {table:<22} {n:>10,}")
            total += n
        print(f"  {'TOTAL':<22} {total:>10,}")


if __name__ == "__main__":
    main()
