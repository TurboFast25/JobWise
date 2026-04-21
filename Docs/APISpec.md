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
