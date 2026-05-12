# Example Flows

---

## Flow 1: Recipe Discovery

Jennifer wants to find a good recipe but doesn't trust generic ratings. She checks a user she respects by calling GET /users/3. She sees that louis_chef has a high trust authority score, so she follows them by calling POST /social/follows.

After following louis_chef, Jennifer requests her personalized feed by calling GET /feed. In the results, she sees Miso Carbonara ranked highly because it was reviewed by someone she trusts.

Jennifer opens the recipe by calling GET /recipes/2 to view the ingredients and instructions.

Jennifer decides to save the recipe by calling POST /cookbook and passes in recipe_id of 2. She receives confirmation that the recipe has been saved.

---

## Flow 2: Recipe Ingestion

Louis finds a Garlic Butter Shrimp Pasta recipe online and wants to add it to the app. He submits the recipe by calling POST /recipes/ingest and includes the title and ingredients.

The system compares the recipe with existing entries and determines it is unique, so it creates a new canonical entry and returns the new recipe ID.

Louis then retrieves the recipe by calling GET /recipes/4 to confirm it is correct, then saves it to his cookbook by calling POST /cookbook.

---

# Testing Results

---

## Recipe Discovery Flow

### Step 1 — Get User Profile (`GET /api/v1/users/3`)

```
curl -X 'GET' \
  'https://flavor-graph.onrender.com/api/v1/users/3' \
  -H 'accept: application/json'
```

Response:

```json
{
    "user_id": 3,
    "username": "louis_chef",
    "trust_authority": 1.4142
}
```

---

### Step 2 — Follow User (`POST /api/v1/social/follows`)

```
curl -X 'POST' \
  'https://flavor-graph.onrender.com/api/v1/social/follows' \
  -H 'accept: application/json' \
  -H 'user-id: 2' \
  -H 'Content-Type: application/json' \
  -d '{
    "followee_id": 3
  }'
```

Response:

```json
{
    "status": "following"
}
```

---

### Step 3 — Get Personalized Feed (`GET /api/v1/feed`)

```
curl -X 'GET' \
  'https://flavor-graph.onrender.com/api/v1/feed' \
  -H 'accept: application/json' \
  -H 'user-id: 2'
```

Response:

```json
[
    {
        "recipe_id": 2,
        "title": "Miso Carbonara",
        "trust_score": 4.2426,
        "trusted_reviewers": [
            "louis_chef"
        ],
        "is_canonical": true
    },
    {
        "recipe_id": 1,
        "title": "Spicy Ramen",
        "trust_score": 0.0,
        "trusted_reviewers": [
            "louis_chef"
        ],
        "is_canonical": true
    },
    {
        "recipe_id": 3,
        "title": "Classic Tomato Sauce",
        "trust_score": 0.0,
        "trusted_reviewers": [
            "louis_chef"
        ],
        "is_canonical": true
    }
]
```

*(Miso Carbonara ranks first because louis_chef gave it a high z_score of 4.2426 — well above his average. The trust score = trust_weight × z_score = 1.0 × 4.2426.)*

---

### Step 4 — Get Recipe Details (`GET /api/v1/recipes/2`)

```
curl -X 'GET' \
  'https://flavor-graph.onrender.com/api/v1/recipes/2' \
  -H 'accept: application/json'
```

Response:

```json
{
    "recipe_id": 2,
    "title": "Miso Carbonara",
    "ingredients": [
        "spaghetti - 200g",
        "eggs - 3",
        "parmesan - 50g",
        "miso paste - 1 tbsp",
        "bacon - 100g"
    ],
    "instructions": [
        "Cook spaghetti until al dente, reserve 1 cup pasta water",
        "Whisk eggs and parmesan together",
        "Fry bacon until crispy",
        "Mix miso paste into egg mixture",
        "Toss hot pasta with bacon, then egg mixture off heat, adding pasta water to loosen"
    ],
    "is_canonical": true
}
```

---

### Step 5 — Save to Cookbook (`POST /api/v1/cookbook`)

```
curl -X 'POST' \
  'https://flavor-graph.onrender.com/api/v1/cookbook' \
  -H 'accept: application/json' \
  -H 'user-id: 2' \
  -H 'Content-Type: application/json' \
  -d '{
    "recipe_id": 2
  }'
```

Response:

```json
{
    "status": "saved"
}
```

---

## Recipe Ingestion Flow

### Step 1 — Ingest New Recipe (`POST /api/v1/recipes/ingest`)

```
curl -X 'POST' \
  'https://flavor-graph.onrender.com/api/v1/recipes/ingest' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Garlic Butter Shrimp Pasta",
    "ingredients": ["spaghetti","shrimp","garlic","butter","parsley","lemon","red pepper flakes","olive oil"]
  }'
```

Response:

```json
{
    "status": "created",
    "canonical_id": 4,
    "confidence": 1.0
}
```

*(No duplicate found — a new canonical recipe was created with ID 4.)*

---

### Step 2 — Verify Recipe (`GET /api/v1/recipes/4`)

```
curl -X 'GET' \
  'https://flavor-graph.onrender.com/api/v1/recipes/4' \
  -H 'accept: application/json'
```

Response:

```json
{
    "recipe_id": 4,
    "title": "Garlic Butter Shrimp Pasta",
    "ingredients": [
        "spaghetti - ",
        "shrimp - ",
        "garlic - ",
        "butter - ",
        "parsley - ",
        "lemon - ",
        "red pepper flakes - ",
        "olive oil - "
    ],
    "instructions": [],
    "is_canonical": true
}
```

---

### Step 3 — Save to Cookbook (`POST /api/v1/cookbook`)

```
curl -X 'POST' \
  'https://flavor-graph.onrender.com/api/v1/cookbook' \
  -H 'accept: application/json' \
  -H 'user-id: 3' \
  -H 'Content-Type: application/json' \
  -d '{
    "recipe_id": 4
  }'
```

Response:

```json
{
    "status": "saved"
}
```

---

### Bonus — Duplicate Detection (`POST /api/v1/recipes/ingest`)

To demonstrate the deduplication logic, we ingested a recipe similar to Classic Tomato Sauce:

```
curl -X 'POST' \
  'https://flavor-graph.onrender.com/api/v1/recipes/ingest' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Quick Tomato Pasta Sauce",
    "ingredients": ["crushed tomatoes","garlic","olive oil","fresh basil","salt"]
  }'
```

Response:

```json
{
    "status": "merged",
    "canonical_id": 3,
    "confidence": 0.8
}
```

*(4 out of 5 submitted ingredients matched Classic Tomato Sauce — Jaccard similarity 0.8 exceeds the 0.5 threshold, so the system merged it into the existing canonical recipe instead of creating a duplicate.)*
