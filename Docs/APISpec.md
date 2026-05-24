# API Specification

**Base URL**: `/api/v1`  
**Content-Type**: `application/json`  
**Authentication**: Protected endpoints require `Authorization: Bearer <JWT>` obtained from `POST /auth/login`.

---

## Authentication

### Login
- **Method**: `POST`
- **Path**: `/auth/login`
- **Description**: Authenticates a user and returns a JWT access token.

**Request**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response**
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

### Create User
- **Method**: `POST`
- **Path**: `/users`
- **Description**: Registers a new user account.

**Request**
```json
{
  "username": "string",
  "email": "string (optional)",
  "password": "string (min 8 characters)"
}
```

**Response**
```json
{
  "user_id": "integer",
  "username": "string",
  "trust_authority": "number"
}
```

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
- **Auth**: Required
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
    "recipe_id": "integer",
    "title": "string",
    "category": "string",
    "trust_score": "number",
    "review_count": "integer",
    "trusted_reviewers": ["string"],
    "is_canonical": "boolean"
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
  "category": "string",
  "ingredients": ["string"],
  "instructions": ["string"],
  "is_canonical": "boolean"
}
```

### 1.2.1 Get Recipe Trust Breakdown
- **Method**: `GET`
- **Path**: `/recipes/{id}/trust_breakdown`
- **Auth**: Required
- **Description**: Explains why a recipe has its trust score for the authenticated user.  
  Trust score = sum of (`trust_weight` × `z_score`) for each followed user who reviewed the recipe.

- **Response**
```json
{
  "recipe_id": "integer",
  "title": "string",
  "trust_score": "number",
  "review_count": "integer",
  "global_average_raw_score": "number | null",
  "trusted_contributions": [
    {
      "username": "string",
      "raw_score": "number",
      "z_score": "number",
      "trust_weight": "number",
      "weighted_contribution": "number"
    }
  ],
  "non_trusted_review_count": "integer"
}
```

### 1.3 Submit Review
- **Method**: `POST`
- **Path**: `/reviews`
- **Auth**: Required
- **Description**: Submits a review and calculates normalized Z-score

- **Request**
```json
{
  "recipe_id": "integer",
  "raw_score": "number (0.0 - 10.0)",
  "comment": "string"
}
```

- **Response**
```json
{
  "review_id": "integer",
  "z_score": "number"
}
```

### 1.4 Ingest Recipe
- **Method**: `POST`
- **Path**: `/recipes/ingest`
- **Description**: Detects duplicates via ingredient similarity

- **Request**
```json
{
  "title": "string",
  "ingredients": ["string"],
  "category": "string (optional)"
}
```

- **Response**
```json
{
  "status": "string (created | duplicate_detected)",
  "canonical_id": "integer",
  "confidence": "number",
  "message": "string (optional, present when duplicate_detected)"
}
```

## Trust Network

The API calls are made in this sequence when a user builds their trust network:
1. `Get User Profile`
2. `Follow User`

### 2.1 Get User Profile
- **Method**: `GET`
- **Path**: `/users/{id}`

- **Response**
```json
{
  "user_id": "integer",
  "username": "string",
  "trust_authority": "number"
}
```

### 2.2 Follow User
- **Method**: `POST`
- **Path**: `/social/follows`
- **Auth**: Required

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
3. `Reorder Cookbook`

### 3.1 Add to Cookbook
- **Method**: `POST`
- **Path**: `/cookbook`
- **Auth**: Required

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
- **Auth**: Required

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
```

### 3.3 Reorder Cookbook
- **Method**: `PUT`
- **Path**: `/cookbook/rankings`
- **Auth**: Required
- **Description**: Replaces the user's full cookbook ranking order. Every saved recipe must appear exactly once with a unique, contiguous rank starting at 1.

- **Request**
```json
{
  "rankings": [
    {"recipe_id": "integer", "personal_rank": "integer"},
    {"recipe_id": "integer", "personal_rank": "integer"}
  ]
}
```

- **Response** — same shape as `GET /cookbook`

- **Errors**
  - `409` — duplicate `personal_rank` values
  - `422` — ranks not contiguous, or rankings do not match the user's full cookbook
  - `404` — recipe ID not in the user's cookbook
