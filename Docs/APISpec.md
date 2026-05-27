# API Specification

**Base URL**: `/api/v1`  
**Content-Type**: `application/json`

---

## 1. Discover + Review Recipe

The API calls are made in this sequence when a user discovers and reviews a recipe:
1. `Get Discovery Feed`
2. `Get Recipe Details`
3. `Submit Review`
4. `Add to Cookbook`

### 1.1 Get Discovery Feed
- **Method**: `GET`
- **Path**: `/feed`
- **Description**: Retrieves recipes ranked by Trust Weight.  
  Score formula:  
  Score_R = sum of (Trust between user u and user v multiplied by the normalized rating that user v gave to recipe R)

- **Query Params**:
  - `limit` (int)
  - `offset` (int)
  - `category` (string)

- **Response**
```json
[
  {
    "recipe_id": "integer", /* unique recipe id */
    "title": "string",
    "trust_score": "number", /* unique recipe id */
    "trusted_reviewers": ["string"],
    "is_canonical": boolean
  }
]
```

### 1.2 Get Recipe Details
- **Method**: `GET`
- **Path**: `/recipes/{id}`
- **Description**: Returns full recipe details

- **Response**
```json

{
  "recipe_id": "integer",
  "title": "string",
  "ingredients": ["string"],
  "instructions": ["string"],
  "is_canonical": "boolean"
}
```

### 1.3 Submit Review
- **Method**: `POST`
- **Path**: `/reviews`
- **Description**: Submits a review and calculates normalized Z-score


- **Request**
```json
{
  "recipe_id": "integer",
  "raw_score": "number, /* 0.0 - 10.0 */
  "comment": "string."
}
```

- **Response**

```json
{
  "review_id": "integer",
  "z_score": "number, /* normalized rating */
}

```

### 1.4 Ingest Recipe
- **Method**: POST
- **Path**: /recipes/ingest
- **Description**: Detects duplicates via ingredient similarity


- **Request**

```json
{
  "title": "string", 
  "ingredients": ["string"] 
}

```

- **Response**

```json
{
  "status": "string", /* created or merged */
  "canonical_id": "integer",
  "confidence": "number" //* similarity score */
}

```

## Trust Network

The API calls are made in this sequence when a user builds their trust network:
1. `Get User Profile`
2. `Follower User`

### 2.1 Get User Profile
- **Method**: GET
- **Path**: /users/{id}


- **Response**

```json
{
  "user_id": "integer",
  "username": "string",
  "trust_authority": "number" /* influence score */
}

```

### 2.2 Follow User
- **Method**: POST
- **Path**: /social/follows


- **Request**

```json
{
  "followee_id": "integer"
}

```

- **Response**

```json
{
  "status": "string"
}

```

## Personal Cookbook

The API calls are made in this sequence when a user manages their saved recipes:
1. `Add to Cookbook`
2. `View Cookbook`

### 3.1 Add to Cookbook

- **Method**: POST
- **Path**: /cookbook

- **Request**

```json
{
  "recipe_id": "integer"
}

```

- **Response**

```json
{
  "status": "string"
}

```

### 3.2 View Cookbook

- **Method**: `GET`
- **Path**: `/cookbook`

- **Response**
```json
{
  "user_rankings": [
    {
      "recipe_id": "integer",
      "personal_rank": "integer",
      "z_score": "number"
    }
  ]
}

## Complex Endpoints

---

### 4.1 Get Similar Recipes

- **Method**: `GET`
- **Path**: `/recipes/{recipe_id}/similar`
- **Description**: Returns recipes similar to the selected recipe using ingredient-overlap similarity.

#### Query Params
- `limit` (int, optional, default: 5)

#### Complex Logic
- Loads the target recipe’s ingredients
- Loads other canonical recipes and their ingredients
- Computes Jaccard similarity between ingredient sets
- Ranks recipes by similarity score
- Returns shared ingredients for explainability

#### Response

```json
[
  {
    "recipe_id": 3,
    "title": "Classic Tomato Sauce",
    "similarity": 0.8,
    "shared_ingredients": [
      "garlic",
      "olive oil",
      "fresh basil"
    ]
  }
]
```

---

### 4.2 Get User Taste Profile

- **Method**: `GET`
- **Path**: `/users/{user_id}/taste-profile`
- **Description**: Builds an analytics profile from a user’s recipe reviews.

#### Complex Logic
- Joins reviews with recipes
- Groups reviews by recipe category
- Computes average score and average z-score per category
- Determines favorite and least favorite categories
- Finds the user’s strongest positive and negative recipe preferences

#### Response

```json
{
  "user_id": 2,
  "username": "jennifer_eats",
  "review_count": 6,
  "average_score": 7.8,
  "favorite_category": "Italian",
  "least_favorite_category": "Dessert",
  "category_breakdown": [
    {
      "category": "Italian",
      "review_count": 3,
      "average_score": 9.0,
      "average_z_score": 1.8
    },
    {
      "category": "Dessert",
      "review_count": 2,
      "average_score": 5.5,
      "average_z_score": -1.2
    }
  ],
  "most_positive_recipe": {
    "recipe_id": 4,
    "title": "Miso Carbonara",
    "z_score": 2.4
  },
  "most_negative_recipe": {
    "recipe_id": 7,
    "title": "Burnt Cheesecake",
    "z_score": -2.1
  }
}
```