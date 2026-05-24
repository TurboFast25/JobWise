# Peer Review Response — V4

**Reviewer:** Agustin Xocua Dimayuga  
**Date:** May 22, 2026  
**Summary:** 12 items received — **12 addressed**

---

## Summary Table

| # | Topic | Decision | Primary files changed |
|---|--------|----------|------------------------|
| 1 | Response models | Addressed | `src/api/schemas.py`, all routers |
| 2 | Explicit transactions | Addressed | `src/api/db_helpers.py`, all write endpoints |
| 3 | Cookbook redundant FK checks | Addressed | `src/api/routers/cookbook.py` |
| 4 | Cookbook rank race condition | Addressed | `src/api/routers/cookbook.py` |
| 5 | `pyproject.toml` + uv | Addressed | `pyproject.toml`, `requirements.txt`, `README` |
| 6 | Feed `review_count` not returned | Addressed | `src/api/routers/feed.py`, `Docs/APISpec.md` |
| 7 | Recipe two-query fetch | Addressed | `src/api/routers/recipes.py` |
| 8 | Ingest loads all recipes | Addressed | `src/api/routers/recipes.py` |
| 9 | Misleading `"merged"` status | Addressed | `src/api/routers/recipes.py`, `Docs/APISpec.md` |
| 10 | Follows redundant round trips | Addressed | `src/api/routers/social.py` |
| 11 | JWT authentication | Addressed | `src/api/auth.py`, `src/api/deps.py`, `src/api/routers/auth.py`, migration `004` |
| 12 | Users redundant duplicate checks | Addressed | `src/api/routers/auth.py` |

---

## Detailed Responses

### 1. Add response models for Swagger / clients

**Feedback:** No `response_model=` on endpoints; clients cannot see response shapes in docs.

**Decision:** Addressed.

**Changes:**
- Created `src/api/schemas.py` with Pydantic models for every request and response type.
- Added `response_model=` to all endpoints across all routers.
- Swagger UI at `/docs` now documents full response schemas.

**Files:** `src/api/schemas.py`, `src/api/routers/*.py`, `src/api/server.py`

---

### 2. Use explicit transactions that roll back on failure

**Feedback:** `db.execute` + manual `commit()` does not guarantee atomicity; failures may leave partial writes.

**Decision:** Addressed.

**Changes:**
- Added `atomic()` context manager in `src/api/db_helpers.py` wrapping `with db.begin():`.
- All mutating endpoints now use `with atomic(db):` instead of manual `db.commit()`.
- Set `autocommit=False, autoflush=False` on `SessionLocal` in `src/database.py`.
- On any exception inside `atomic()`, SQLAlchemy rolls back the transaction automatically.

**Endpoints updated:** `POST /cookbook`, `POST /reviews`, `POST /recipes/ingest`, `POST /social/follows`, `POST /users`

---

### 3. `POST /cookbook` — remove unnecessary FK pre-check queries

**Feedback:** Foreign keys on `cookbook_entries` already enforce user/recipe validity; use a single insert and catch referential integrity errors.

**Decision:** Addressed.

**Changes:**
- Removed three pre-check `SELECT` queries (user exists, recipe exists, duplicate entry).
- Replaced with a single `INSERT` inside `atomic()`.
- Added `map_integrity_error()` in `src/api/db_helpers.py` and a global FastAPI handler in `server.py` to map Postgres errors:
  - FK violation (`23503`) → `404` with `"User not found"` or `"Recipe not found"`
  - Unique violation on `uq_cookbook_entry` → `409` `"Already in your cookbook"`

**Before:** 4–5 DB round trips. **After:** 2 (user row lock + insert).

---

### 4. `POST /cookbook` — lost-update race on `personal_rank`

**Feedback:** Reading `COUNT(*)` in Python then inserting causes duplicate ranks under concurrent requests.

**Decision:** Addressed.

**Changes:**
- Rank is computed inside the database via scalar subquery:
  ```sql
  SELECT COALESCE(MAX(personal_rank), 0) + 1 FROM cookbook_entries WHERE user_id = :uid
  ```
- User row is locked first with `SELECT user_id FROM users WHERE user_id = :uid FOR UPDATE` to serialize concurrent cookbook inserts for the same user.
- Entire operation runs inside `atomic()`.

**Files:** `src/api/routers/cookbook.py`

---

### 5. Add `pyproject.toml` and uv for reproducible local setup

**Feedback:** Local setup failed; no `pyproject.toml`; recommend `uv sync`.

**Decision:** Addressed.

**Changes:**
- Added `pyproject.toml` with all runtime and dev dependencies.
- Updated `README` with setup instructions: `uv sync`, `uv run alembic upgrade head`, `uv run uvicorn ...`
- Kept `requirements.txt` for Render deployment (`pip install -r requirements.txt`).

**Files:** `pyproject.toml`, `requirements.txt`, `README`

---

### 6. `GET /feed` — `review_count` selected but not returned

**Feedback:** (Noted as `POST /feed/` in review; our endpoint is `GET /feed`.) `review_count` is computed but omitted from the response.

**Decision:** Addressed.

**Changes:**
- Added `review_count: int` to `FeedItemResponse` in `src/api/schemas.py`.
- Feed handler now returns `review_count` for each recipe.
- Updated `Docs/APISpec.md` response schema.

**Note:** `review_count` is still used in `ORDER BY` for secondary sort when trust scores are tied.

---

### 7. `GET /recipes/{recipe_id}` — combine two queries with a join

**Feedback:** Recipe and ingredients should be fetched in one query using the FK relationship.

**Decision:** Addressed.

**Changes:**
- Replaced two separate `SELECT` statements with one query using `LEFT JOIN ingredients` and `array_agg(...)`.
- Recipe-not-found is detected when the grouped query returns no rows.
- `LEFT JOIN` preserves recipes that have no ingredients (edge case).

**Files:** `src/api/routers/recipes.py`

---

### 8. `POST /recipes/ingest` — loading all canonical recipes into memory

**Feedback:** Full-table load will not scale and may timeout.

**Decision:** Addressed.

**Changes:**
- Candidate recipes are pre-filtered in SQL to only those sharing at least one ingredient name (case-insensitive):
  ```sql
  WHERE r.recipe_id IN (
      SELECT DISTINCT i2.recipe_id FROM ingredients i2
      WHERE lower(trim(i2.name)) = ANY(:incoming_names)
  )
  ```
- Jaccard similarity is computed in Python only on this reduced candidate set.
- New recipes with no ingredient overlap skip the similarity scan entirely.

**Files:** `src/api/routers/recipes.py`

---

### 9. `POST /recipes/ingest` — `"merged"` status is misleading

**Feedback:** No merge actually occurs; user data is not applied. Suggested `request_rejected`.

**Decision:** Addressed.

**Changes:**
- Renamed status from `"merged"` to `"duplicate_detected"`.
- Added `message` field to `IngestResponse`: `"A similar recipe already exists; no new entry was created."`
- Updated `Docs/APISpec.md` to document `created` and `duplicate_detected` statuses.

**Rationale for name choice:** `duplicate_detected` is more descriptive than `request_rejected` while clearly communicating that no write occurred.

---

### 10. `POST /social/follows` — unnecessary DB round trips

**Feedback:** Use a single `INSERT ... SELECT` inside a transaction; let constraints handle validation.

**Decision:** Addressed.

**Changes:**
- Removed four pre-check queries.
- Single statement:
  ```sql
  INSERT INTO follows (follower_id, followee_id, trust_weight)
  SELECT :me, :them, 1.0
  WHERE EXISTS (SELECT 1 FROM users WHERE user_id = :me)
    AND EXISTS (SELECT 1 FROM users WHERE user_id = :them)
  RETURNING follow_id
  ```
- Zero rows returned → `404 User not found`.
- `IntegrityError` on `uq_follow` → `409 You're already following this user`.
- Self-follow check kept in application layer (`400`) since no DB constraint exists for it.

**Files:** `src/api/routers/social.py`

---

### 11. JWT authentication instead of `user-id` header

**Feedback:** Recommends JWT for authenticating users on protected endpoints.

**Decision:** Addressed.

**Changes:**
- Added `password_hash` column via Alembic migration `004_add_password_hash.py`.
- Seeded users (from migration 002) receive bcrypt hash of `password123` for local testing.
- New module `src/api/auth.py`: bcrypt password hashing, JWT create/decode.
- New module `src/api/deps.py`: `get_current_user_id()` dependency reading `Authorization: Bearer <token>`.
- New endpoints:
  - `POST /api/v1/auth/login` — returns JWT access token
  - `POST /api/v1/users` — moved to `auth` router; now requires `password` (min 8 chars)
- Protected endpoints now use `Depends(get_current_user_id)` instead of `user-id` header:
  - `GET /feed`, `POST /reviews`, `POST /cookbook`, `GET /cookbook`, `POST /social/follows`
- `JWT_SECRET_KEY` env var supported (defaults to dev-only value).

**Files:** `src/api/auth.py`, `src/api/deps.py`, `src/api/routers/auth.py`, `alembic/versions/004_add_password_hash.py`, all protected routers

---

### 12. `POST /users` — three DB trips for duplicate checking

**Feedback:** Unique constraints already exist; use single insert and catch violations.

**Decision:** Addressed.

**Changes:**
- Removed pre-check `SELECT` queries for username and email.
- Single `INSERT ... RETURNING` inside `atomic()`.
- `IntegrityError` mapped via global handler using `map_integrity_error()`:
  - Username unique → `409 Username is already taken`
  - Email unique → `409 Email is already registered`
- Username uniqueness constraint existed in migration `001`; email uniqueness in migration `003`.

**Files:** `src/api/routers/auth.py`

---

## New / Shared Infrastructure

| File | Purpose |
|------|---------|
| `src/api/schemas.py` | All Pydantic request/response models |
| `src/api/db_helpers.py` | `atomic()` transaction helper + `map_integrity_error()` |
| `src/api/auth.py` | bcrypt + JWT utilities |
| `src/api/deps.py` | `get_current_user_id` FastAPI dependency |
| `src/api/routers/auth.py` | Login + user registration |
| `alembic/versions/004_add_password_hash.py` | Password column for JWT auth |
| `pyproject.toml` | uv-compatible dependency manifest |

---

## Local Setup (post-changes)

```bash
uv sync
cp .env.example .env   # set POSTGRES_URI and optionally JWT_SECRET_KEY
uv run alembic upgrade head
uv run uvicorn src.api.server:app --reload
```

Login for seeded users:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "jennifer_eats", "password": "password123"}'
```

Use returned token on protected routes:
```bash
curl http://localhost:8000/api/v1/feed \
  -H "Authorization: Bearer <token>"
```

---

## API Breaking Changes

1. **`user-id` header removed** from protected endpoints — use `Authorization: Bearer <JWT>`.
2. **`POST /users` requires `password`** field (min 8 characters).
3. **Ingest duplicate status** changed from `"merged"` to `"duplicate_detected"` with optional `message`.
4. **Feed response** includes new `review_count` field.

These are documented in `Docs/APISpec.md`.

---

## Re-Audit (May 22, 2026)

A second full pass was performed against all 12 review items. Results:

| Check | Status |
|-------|--------|
| All API endpoints have `response_model` | Pass |
| All write endpoints use `atomic()` | Pass |
| No manual `db.commit()` left in routers | Pass |
| Cookbook: single insert + DB-side rank + `FOR UPDATE` | Pass |
| Feed returns `review_count` | Pass |
| Recipe details: single JOIN query | Pass |
| Ingest: candidate pre-filter (not full table scan) | Pass |
| Ingest status: `duplicate_detected` (not `merged`) | Pass |
| Follows: single `INSERT ... SELECT` | Pass |
| Users: single insert + constraint handling | Pass |
| JWT on all protected routes (OpenAPI shows `HTTPBearer`) | Pass |
| `pyproject.toml` + `uv sync` works | Pass |
| Migration 004 seed password hash verifies | Pass |
| App imports cleanly with `POSTGRES_URI` set | Pass |

### Fixes applied during re-audit

1. **Removed unused imports** in `recipes.py` and `cookbook.py`.
2. **Hardened integrity error mapping** to prefer Postgres `diag.constraint_name` over broad string matching.
3. **Added whitespace-only ingredient validation** on ingest.
4. **Initialized result variables** before `try/atomic` blocks in routers.

### Final refinement pass

1. **Global `IntegrityError` handler** in `server.py` — removed duplicated `try/except` blocks from every router.
2. **SQL constants extracted** — feed, recipe detail, and candidate queries are module-level strings (no f-string SQL).
3. **Feed category filter** uses `(:category IS NULL OR ...)` bind parameter instead of dynamic SQL concatenation.
4. **Pydantic validators** on `CreateUserRequest`, `LoginRequest`, and `IngestRequest` — strip/normalize inputs at the schema layer.
5. **`IngestResponse.status`** typed as `Literal["created", "duplicate_detected"]`.
6. **bcrypt hashing moved outside transactions** in user registration (avoid holding DB locks during slow hash).
7. **JWT `exp` claim** uses integer Unix timestamp per RFC 7519.
8. **`verify_password`** safely returns `False` on malformed hashes instead of raising.
9. **Database engine** uses `pool_pre_ping=True` and `expire_on_commit=False`.
10. **Helper extraction** in `recipes.py` — `_normalize_ingredients`, `_format_ingredient`, `_parse_instructions`.
11. **Return type annotations** added on all route handlers.
12. **Package `__init__.py` files** added under `src/`, `src/api/`, and `src/api/routers/`.

### Known stale docs (not code bugs)

- `v1_manual_test_results.md` and `v2_manual_test_results.md` still show the old `user-id` header and `"merged"` ingest status. These are historical V1/V2 test snapshots. Use `README` and `Docs/APISpec.md` for current V4 behavior.
