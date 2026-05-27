## Case 1 — Lost Update on `personal_rank` (Cookbook)

## Endpoint:`POST /cookbook` — [`src/api/routers/cookbook.py`](src/api/routers/cookbook.py)
When a user adds a recipe to their cookbook the endpoint first reads the current count of their cookbook entries and then inserts a new entry at rank `count + 1`.

```python
count = db.execute(
    text("SELECT COUNT(*) AS cnt FROM cookbook_entries WHERE user_id = :uid"),
    {"uid": user_id}
).fetchone()

db.execute(
    text("INSERT INTO cookbook_entries (user_id, recipe_id, personal_rank) VALUES (:uid, :rid, :rank)"),
    {"uid": user_id, "rid": body.recipe_id, "rank": count.cnt + 1}
)
```

### Sequence Diagram
```
T1 (add recipe 10)                          T2 (add recipe 20)
------------------                          -------------------
SELECT COUNT(*) → 5
                                            SELECT COUNT(*) → 5
                                            (T1 hasn't committed yet, still sees 5)
INSERT personal_rank = 6
COMMIT
                                            INSERT personal_rank = 6  ← same rank!
                                            COMMIT

Result: two cookbook entries for user 42 both have personal_rank = 6.
```

### Fix and Why

The fix collapses the read and the write into a **single atomic SQL statement**, eliminating the gap between the count read and the insert:

```sql
INSERT INTO cookbook_entries (user_id, recipe_id, personal_rank)
SELECT :uid, :rid, COUNT(*) + 1
FROM cookbook_entries
WHERE user_id = :uid
```

Because the `COUNT(*)` subquery and the `INSERT` happen within the same statement execution, the database ensures no other row with the same `user_id` can be inserted between the count being observed and the row being written. This fix works correctly under PostgreSQL's default **READ COMMITTED** isolation level, no isolation level upgrade is needed because the race is caused by the application-level gap, not by snapshot semantics.





## Case 2 — Phantom Read in Recipe Deduplication (Ingest)

## Endpoint: `POST /recipes/ingest` — [`src/api/routers/recipes.py`](src/api/routers/recipes.py)
The ingest endpoint is responsible for preventing duplicate canonical recipes. It reads all existing canonical recipes, computes Jaccard ingredient similarity, and only creates a new recipe if the best similarity score is below 0.5.

```python
existing_recipes = db.execute(
    text("""
        SELECT r.recipe_id, array_agg(i.name) AS ingredients
        FROM recipes r
        JOIN ingredients i ON i.recipe_id = r.recipe_id
        WHERE r.is_canonical = true
        GROUP BY r.recipe_id
    """)
).fetchall()

# ... compute Jaccard similarity ...

if best_score >= 0.5 and best_match:
    return {"status": "merged", ...}

# No match — create a new recipe
new_recipe = db.execute(text("INSERT INTO recipes ... RETURNING recipe_id"), ...).fetchone()
```

When two nearly identical recipes are submitted simultaneously, both transactions read the canonical recipe table before either has committed a new row. Neither sees the other's pending recipe, so both conclude that no duplicate exists and both proceed to insert, creating two duplicate canonical recipes that violate the invariant the endpoint is designed to enforce.

### Sequence Diagram
```
T1 (ingest "Spaghetti Carbonara")           T2 (ingest "Carbonara Spaghetti")
[eggs, bacon, pasta, cheese]                [pasta, bacon, eggs, pecorino]
---------------------------------           ---------------------------------
SELECT all canonical recipes
Jaccard best score = 0.1 → no match
                                            SELECT all canonical recipes
                                            Jaccard best score = 0.1 → no match
                                            (T1's insert not committed yet, invisible)
INSERT recipe_id = 101
INSERT ingredients
COMMIT
                                            INSERT recipe_id = 102  ← duplicate!
                                            INSERT ingredients
                                            COMMIT

Result: two canonical recipes exist for the same dish.
```

### Fix and Why

We set the transaction isolation level to **SERIALIZABLE** at the start of the ingest transaction:

```python
db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
```

Under SERIALIZABLE, PostgreSQL tracks read/write dependencies between concurrent transactions. T2's read of the canonical recipes table creates a dependency on T1's write to that same table. When both transactions try to commit, PostgreSQL detects the cycle and aborts one with a serialization failure. The aborted request would need to be retried by the client, at which point the Jaccard scan runs again, this time seeing T1's committed recipe, and correctly returns `"merged"` instead of inserting a duplicate.






## Case 3 — Lost Update on `trust_authority` (Concurrent Reviews)

## Endpoint: `POST /reviews` — [`src/api/routers/reviews.py`](src/api/routers/reviews.py)
After inserting a new review the endpoint recalculates the user's `trust_authority` by taking the average of the absolute z-scores across all of that user's reviews:

```python
db.execute(
    text("""
        UPDATE users
        SET trust_authority = (
            SELECT AVG(ABS(z_score)) FROM reviews WHERE user_id = :uid
        )
        WHERE user_id = :uid
    """),
    {"uid": user_id}
)
```

When two reviews for the same user are submitted concurrently (for two different recipes), each transaction inserts its own review and then runs this `UPDATE`. Under **READ COMMITTED** (PostgreSQL's default), each transaction's `UPDATE` subquery only sees reviews that have been committed at the moment the subquery executes. If both `UPDATE` statements execute before either transaction commits, each one sees only 11 rows (the 10 pre-existing reviews plus its own newly inserted row), not all 12. Whichever transaction commits last will overwrite the other's `trust_authority` with a value computed from an incomplete set of reviews, so the final `trust_authority` reflects only 11 of the 12 reviews instead of all 12.

### Sequence Diagram
```
User 42 already has 10 reviews.

T1 (review recipe 5, score 9.0)             T2 (review recipe 7, score 2.0)
-------------------------------             -------------------------------
SELECT AVG/STDDEV/COUNT → count=10
z1 = (9.0 - 7.0) / 1.5 = 1.33
INSERT review, z_score = 1.33
                                            SELECT AVG/STDDEV/COUNT → count=10
                                            (T1 not committed yet, still sees 10)
                                            z2 = (2.0 - 7.0) / 1.5 = -3.33
                                            INSERT review, z_score = -3.33
UPDATE trust_authority = AVG(ABS(z))
→ sees 11 rows (T2 not committed yet)
COMMIT  →  trust_authority = X
                                            UPDATE trust_authority = AVG(ABS(z))
                                            → sees 11 rows (only its own + 10 old)
                                            COMMIT  →  trust_authority = Y  ← overwrites X

Result: trust_authority is based on 11 reviews instead of all 12.
```

### Fix and Why

We lock the user row with `SELECT ... FOR UPDATE` at the start of the transaction, before any reads or writes on the reviews table:

```python
db.execute(text("SELECT 1 FROM users WHERE user_id = :id FOR UPDATE"), {"id": user_id})
```

This forces two concurrent review submissions for the same user to serialize against each other. T2 blocks at this line until T1 commits and releases the lock. When T2 then proceeds, its `UPDATE trust_authority` subquery reads from a fully committed state that includes T1's new review, so `trust_authority` is always computed over the complete set of reviews. The lock is held for the duration of the transaction and released automatically on commit.
