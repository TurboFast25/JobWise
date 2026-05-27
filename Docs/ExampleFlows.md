# Example Flows

Use seeded users after `alembic upgrade head`:

| user_id | username      | password      |
|---------|---------------|---------------|
| 1       | diego_cooks   | password123   |
| 2       | jennifer_eats | password123   |
| 3       | louis_chef    | password123   |

| recipe_id | title                 | category |
|-----------|-----------------------|----------|
| 1         | Spicy Ramen           | —        |
| 2         | Miso Carbonara        | Italian  |
| 3         | Classic Tomato Sauce  | —        |

Authenticate with `POST /api/v1/auth/login`, then pass `Authorization: Bearer <token>` on protected routes. The `user-id` header is also supported for testing; invalid IDs return **404 User not found**.

---

## Recipe Discovery Example Flow

Jennifer (user 2) wants a trusted Italian recipe. She checks **louis_chef** (user 3), follows him, and gets an Italian feed where **Miso Carbonara** (recipe 2) ranks highly because Louis reviewed it.

1. `GET /api/v1/users/3` — high `trust_authority`
2. `POST /api/v1/social/follows` with `followee_id: 3` (as Jennifer)
3. `GET /api/v1/feed?category=Italian` — Miso Carbonara with non-zero `trust_score` and `trusted_reviewers`
4. `GET /api/v1/recipes/2`
5. `POST /api/v1/cookbook` with `recipe_id: 2`

---

## Cook and Review Example Flow

Diego (user 1) reviews **Spicy Ramen** (recipe 1), checks his cookbook, and saves the recipe.

1. `GET /api/v1/recipes/1`
2. `POST /api/v1/reviews` with `recipe_id: 1`, `raw_score: 7.5`
3. `GET /api/v1/cookbook`
4. `POST /api/v1/cookbook` with `recipe_id: 1` (if not already saved)

---

## Recipe Ingestion Example Flow

Louis submits a tomato sauce that matches **Classic Tomato Sauce** (recipe 3). The API returns `duplicate_detected` with `canonical_id: 3` instead of creating a duplicate.

1. `POST /api/v1/recipes/ingest` with overlapping ingredients (see manual test guide)
2. Response: `"status": "duplicate_detected"`, `"canonical_id": 3`
3. `GET /api/v1/recipes/3`
4. `POST /api/v1/cookbook` with `recipe_id: 3`

---

## Edge cases covered by tests

- **Invalid user** (`user-id: 125` or bad JWT) → 404 / 401, not feed data or empty cookbook masquerading as valid
- **Blank ingredients** (`""`, `"  "`) → 422 validation error
- **Invalid recipe on review** → 404 Recipe not found (fast pre-check)
- **Duplicate review / cookbook / username** → 409 with clear message
