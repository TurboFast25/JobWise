# Example workflow

## Cook and Review Example Flow

Diego has just finished cooking a spicy ramen recipe and wants to leave a review. First, Diego retrieves the recipe details by calling GET /recipes/1 to make sure he is reviewing the correct recipe.

Diego then submits his review by calling POST /reviews and passes in a score of 7.5 along with a short comment. The system processes the review and calculates a normalized score based on Diego's rating history.

Diego then checks his saved recipes by calling GET /cookbook and sees his list.

To save the recipe for later, Diego:
- calls POST /cookbook and passes in the recipe_id of 1.
- receives confirmation that the recipe has been saved.

Diego has now reviewed and saved the recipe in the app.

---

# Testing results

## Step 1 — Get Recipe Details (`GET /api/v1/recipes/1`)

```
curl -X 'GET' \
  'https://flavor-graph.onrender.com/api/v1/recipes/1' \
  -H 'accept: application/json'
```

Response:

```json
{
    "recipe_id": 1,
    "title": "Spicy Ramen",
    "ingredients": [
        "ramen noodles - 2 servings",
        "miso paste - 2 tbsp",
        "chili paste - 1 tbsp",
        "soft boiled egg - 2",
        "nori - 2 sheets",
        "chicken broth - 4 cups"
    ],
    "instructions": [
        "Boil broth with miso paste and chili paste for 10 minutes",
        "Cook ramen noodles separately",
        "Soft boil eggs for 6 minutes",
        "Combine noodles and broth in a bowl",
        "Top with egg sliced in half and nori sheets"
    ],
    "is_canonical": true
}
```

---

## Step 2 — Submit Review (`POST /api/v1/reviews`)

```
curl -X 'POST' \
  'https://flavor-graph.onrender.com/api/v1/reviews' \
  -H 'accept: application/json' \
  -H 'user-id: 1' \
  -H 'Content-Type: application/json' \
  -d '{
    "recipe_id": 1,
    "raw_score": 7.5,
    "comment": "Great depth of flavor, the miso and chili balance is spot on."
  }'
```

Response:

```json
{
    "review_id": 1,
    "z_score": 0.0
}
```

*(z_score is 0.0 because this is Diego's first review — no prior distribution to normalize against yet.)*

---

## Step 3 — Save Recipe to Cookbook (`POST /api/v1/cookbook`)

```
curl -X 'POST' \
  'https://flavor-graph.onrender.com/api/v1/cookbook' \
  -H 'accept: application/json' \
  -H 'user-id: 1' \
  -H 'Content-Type: application/json' \
  -d '{
    "recipe_id": 1
  }'
```

Response:

```json
{
    "status": "saved"
}
```

---

## Step 4 — View Cookbook (`GET /api/v1/cookbook`)

```
curl -X 'GET' \
  'https://flavor-graph.onrender.com/api/v1/cookbook' \
  -H 'accept: application/json' \
  -H 'user-id: 1'
```

Response:

```json
{
    "user_rankings": [
        {
            "recipe_id": 1,
            "personal_rank": 1,
            "z_score": 0.0
        }
    ]
}
```
