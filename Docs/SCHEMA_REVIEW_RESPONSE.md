# Schema & API Design Review Response

Reviewer feedback mapped to status after migration `006_schema_review_fixes`.

| # | Feedback | Status |
|---|----------|--------|
| 1 | `USERS.trust_authority` violates 3NF | **Addressed** — column removed; computed at read time via `TRUST_AUTHORITY_SUBQUERY` |
| 2 | `INGREDIENTS` should be many-to-many | **Addressed** — `ingredient_catalog` + `recipe_ingredients`; old `ingredients` table dropped |
| 3 | `RECIPES.confidence` misplaced | **Addressed** — moved to `recipe_merges`; column removed from `recipes` |
| 4 | `RECIPES.canonical_id` cycle risk | **Addressed** — CHECK constraints: no self-reference; canonical rows cannot point elsewhere |
| 5 | `FOLLOWS.trust_weight` stale | **Addressed** — column removed; scoring uses constant `1.0` at query time |
| 6 | `REVIEWS` unique `(user_id, recipe_id)` | **Already existed** — `uq_user_recipe_review` since migration `001` |
| 7 | `REVIEWS.z_score` should not be stored | **Addressed** — column removed; computed via `Z_SCORE_EXPR` + `USER_STATS_LATERAL` |
| 8 | No `author_id` on `RECIPES` | **Addressed** — `author_id` FK added; set on ingest when JWT provided |
| 9 | `COOKBOOK_ENTRIES.personal_rank` conflicts | **Addressed** — ranks normalized; `UNIQUE(user_id, personal_rank)` enforced |
| 10 | No `updated_at` | **Addressed** — added to `users`, `recipes`, `follows`, `reviews`, `cookbook_entries` |
| 11 | `GET /feed` not RESTful | **Addressed** — alias `GET /recipes/feed` (legacy `/feed` retained) |
| 12 | `POST /reviews` body has `recipe_id` | **Addressed** — `POST /recipes/{recipe_id}/reviews` added (legacy route retained) |
| 13 | Ingredients as flat strings | **Addressed** — `[{ "name", "quantity" }]` in recipe detail response |
| 14 | `/cookbook` not user-scoped in path | **Documented** — identity from JWT / validated `user-id` header; see APISpec |
| 15 | `POST /social/follows` inconsistent | **Addressed** — alias `POST /follows` (legacy path retained) |
| 16 | `POST /recipes/ingest` under-documented | **Addressed** — expanded APISpec |
| 17 | Follow response only `{ status }` | **Addressed** — returns `follow_id`, `follower_id`, `followee_id`, `created_at`, `trust_weight` |
| 18 | Random `user_id` spoofing | **Addressed** — JWT via `POST /auth/login` + `password_hash` on users; header auth validates user exists |

## Invariants (canonical recipes)

- `canonical_id IS NULL OR canonical_id != recipe_id`
- If `is_canonical = true`, then `canonical_id` must be `NULL` (one-hop: variants point to canonical, not vice versa)

## Derived values (computed at read time)

- **z_score** — from reviewer’s `raw_score` vs that reviewer’s mean/stddev
- **trust_authority** — `AVG(ABS(z_score))` over a user’s reviews
- **trust_weight** — `1.0` for all follow edges in scoring queries
