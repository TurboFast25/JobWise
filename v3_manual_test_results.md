# V3 Manual Test Guide

Base URL: `https://flavor-graph.onrender.com/api/v1` (or `http://localhost:8000/api/v1` locally)

Run `alembic upgrade head` before testing so migration `005` seeds trust demo data.

## Login (Jennifer)

```bash
curl -s -X POST "$BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"jennifer_eats","password":"password123"}'
```

Use `access_token` as `TOKEN` below, or use `-H "user-id: 2"` for header auth.

---

## Flow 1: Recipe Discovery

### GET /users/3 (louis_chef)

```bash
curl -s "$BASE/api/v1/users/3"
```

Expected: `trust_authority` > 0 after migration 005.

### POST /social/follows

```bash
curl -s -X POST "$BASE/api/v1/social/follows" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"followee_id": 3}'
```

Expected: `{"status":"following"}` or 409 if already following.

### GET /feed?category=Italian

```bash
curl -s "$BASE/api/v1/feed?category=Italian" \
  -H "Authorization: Bearer $TOKEN"
```

Expected: Miso Carbonara (`recipe_id: 2`), `trust_score` > 0, `trusted_reviewers` includes `louis_chef`, `review_count` present.

### GET /recipes/2

```bash
curl -s "$BASE/api/v1/recipes/2"
```

### POST /cookbook

```bash
curl -s -X POST "$BASE/api/v1/cookbook" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"recipe_id": 2}'
```

Expected: `{"status":"saved"}` or 409 if already saved.

---

## Flow 2: Cook and Review (Diego, user 1)

```bash
TOKEN_DIEGO=$(curl -s -X POST "$BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"diego_cooks","password":"password123"}' | jq -r .access_token)

curl -s "$BASE/api/v1/recipes/1"

curl -s -X POST "$BASE/api/v1/reviews" \
  -H "Authorization: Bearer $TOKEN_DIEGO" \
  -H "Content-Type: application/json" \
  -d '{"recipe_id": 1, "raw_score": 7.5, "comment": "Great ramen"}'

curl -s "$BASE/api/v1/cookbook" -H "Authorization: Bearer $TOKEN_DIEGO"
```

---

## Flow 3: Ingest duplicate (Classic Tomato Sauce)

```bash
curl -s -X POST "$BASE/api/v1/recipes/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "tomato sauce",
    "ingredients": ["crushed tomatoes", "garlic", "olive oil", "fresh basil"],
    "category": "Italian"
  }'
```

Expected:

```json
{
  "status": "duplicate_detected",
  "canonical_id": 3,
  "confidence": 0.5,
  "message": "A similar recipe already exists; no new entry was created."
}
```

---

## Edge case tests

### Invalid user on feed (404)

```bash
curl -s "$BASE/api/v1/feed?category=Italian" -H "user-id: 125"
```

Expected: `{"detail":"User not found"}`

### Invalid user on cookbook (404)

```bash
curl -s "$BASE/api/v1/cookbook" -H "user-id: 125"
```

Expected: `{"detail":"User not found"}`

### Blank ingredients (422)

```bash
curl -s -X POST "$BASE/api/v1/recipes/ingest" \
  -H "Content-Type: application/json" \
  -d '{"title":"test","ingredients":["", "  "],"category":"test"}'
```

Expected: 422 validation error.

### Invalid recipe on review (404, fast)

```bash
curl -s -X POST "$BASE/api/v1/reviews" \
  -H "Authorization: Bearer $TOKEN_DIEGO" \
  -H "Content-Type: application/json" \
  -d '{"recipe_id": 10000, "raw_score": 10, "comment": "x"}'
```

Expected: `{"detail":"Recipe not found"}`

### Duplicate username (409)

```bash
curl -s -X POST "$BASE/api/v1/users" \
  -H "Content-Type: application/json" \
  -d '{"username":"diego_cooks","email":"x@test.com","password":"password12345"}'
```

Expected: `{"detail":"Username is already taken"}`
