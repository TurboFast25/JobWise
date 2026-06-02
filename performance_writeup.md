# Performance Writeup

---

## Fake Data Modeling

The fake data generation script is at [seed_data.py](seed_data.py).

### Row Counts

| Table              | Rows      |
|--------------------|-----------|
| users              | 10,000    |
| recipes            | 50,000    |
| ingredients        | 275,112   |
| reviews            | 500,000   |
| follows            | 100,000   |
| cookbook_entries   | 100,000   |
| **TOTAL**          | **1,035,112** |

### Distribution Justification

**10,000 users** — A recipe social network at mid-scale launch. Not everyone who signs up is active, but 10K registered accounts is a realistic early-growth milestone before viral spread.

**50,000 recipes** — Recipe catalogs grow primarily through user submission, not by users browsing. 5 recipes per user on average is conservative and accounts for many lurker accounts that never post. A dedicated cooking platform like AllRecipes had tens of thousands of recipes before it became mainstream.

**275,112 ingredients (~5.5 per recipe)** — Real recipes average 6–8 ingredients. We used a random range of 3–8 per recipe, giving an average of ~5.5. This is slightly conservative to keep the table size manageable.

**500,000 reviews (~50 per user)** — Active users on recommendation-driven platforms (Letterboxd, Goodreads) often rate 50–200 items. 50 reviews per user is a reasonable floor for users who engage enough to generate meaningful trust scores. With 50K recipes and 10K users, each recipe gets reviewed by roughly 10 different users on average, which produces non-trivial ranking data.

**100,000 follows (~10 per user)** — Social graphs on food platforms tend to be sparse. Users follow food bloggers or close friends, not hundreds of people. 10 follows per user reflects a modestly connected social graph where trust scores are meaningful but not diluted.

**100,000 cookbook entries (~10 per user)** — Users save recipes they intend to cook or already love. 10 saves per user is consistent with casual engagement — enough to populate a useful personal feed without representing compulsive hoarding behavior.

---

## Performance Results of Hitting Endpoints

All timings were measured by running the raw SQL queries directly against the local postgres instance with `\timing on`. This reflects execution time without HTTP or serialization overhead.

| Endpoint                        | Time (ms) |
|---------------------------------|-----------|
| GET /users/{id}                 | 0.3       |
| GET /users/{id}/taste-profile   | 0.3       |
| GET /cookbook                   | 1.0       |
| GET /recipes/{id} (recipe row)  | 0.8       |
| GET /recipes/{id} (ingredients) | 18.8      |
| GET /recipes/{id}/similar       | 162       |
| **GET /feed**                   | **401**   |

**The slowest endpoint is `GET /feed` at 401 ms.**

---

## Performance Tuning

### EXPLAIN Before Indexes

```
EXPLAIN ANALYZE
SELECT
    r.recipe_id, r.title, r.category, r.is_canonical,
    COALESCE(SUM(f.trust_weight * rev.z_score), 0) AS trust_score,
    COUNT(DISTINCT rev.review_id) AS review_count,
    array_agg(DISTINCT u.username) FILTER (WHERE f.follower_id = 1 AND u.username IS NOT NULL) AS trusted_reviewers
FROM recipes r
LEFT JOIN reviews rev ON rev.recipe_id = r.recipe_id
LEFT JOIN follows f ON f.followee_id = rev.user_id AND f.follower_id = 1
LEFT JOIN users u ON u.user_id = rev.user_id
WHERE r.is_canonical = true
GROUP BY r.recipe_id, r.title, r.category, r.is_canonical
ORDER BY trust_score DESC, review_count DESC
LIMIT 20 OFFSET 0;
```

```
 Limit  (cost=95955.53..95955.58 rows=20 width=89) (actual time=399.948..399.951 rows=20 loops=1)
   ->  Sort  (cost=95955.53..96080.53 rows=50000 width=89) (actual time=399.946..399.948 rows=20 loops=1)
         Sort Key: (COALESCE(sum(...))) DESC, (count(DISTINCT rev.review_id)) DESC
         Sort Method: top-N heapsort  Memory: 29kB
         ->  GroupAggregate  (cost=85250.05..94625.05 rows=50000 width=89) (actual time=282.910..393.114 rows=50000 loops=1)
               Group Key: r.recipe_id
               ->  Sort  (cost=85250.05..86500.05 rows=500000 width=77) (actual time=282.872..343.131 rows=500002 loops=1)
                     Sort Key: r.recipe_id, rev.review_id
                     Sort Method: external merge  Disk: 42760kB
                     ->  Hash Left Join  (cost=2596.34..15703.13 rows=500000 width=77) ...
                           ->  Hash Left Join  (cost=2189.34..13983.07 rows=500000 width=69) ...
                                 ->  Hash Right Join ...
                                       ->  Seq Scan on reviews rev  (actual time=0.017..13.198 rows=500000 loops=1)
                                       ->  Hash  (Seq Scan on recipes r, Filter: is_canonical, rows=50000)
                                 ->  Hash  (Index Scan using uq_follow on follows f, follower_id=1, rows=10)
                           ->  Hash  (Seq Scan on users u, rows=10000)
 Execution Time: 401.154 ms
```

**What this means:** The planner performs a sequential scan of all 500K reviews and all 50K recipes, hash-joins them, then sorts the full 500K-row result set to feed the GroupAggregate. The critical line is `Sort Method: external merge Disk: 42760kB` — the sort cannot fit in memory and spills 42 MB to disk. This disk I/O is the dominant cost. There is no index on `reviews.recipe_id`, so the planner cannot use an ordered index scan to feed the aggregate and instead must sort everything from scratch.

### Indexes Added

```sql
-- Covering index: lets the planner use an index-only scan on reviews,
-- providing all needed columns (recipe_id, user_id, z_score, review_id)
-- without touching the heap at all.
CREATE INDEX idx_reviews_recipe_covering ON reviews(recipe_id) INCLUDE (user_id, z_score, review_id);

-- Partial index: the feed WHERE clause filters is_canonical = true on every run.
-- A partial index only stores canonical recipe rows, reducing index size.
CREATE INDEX idx_recipes_canonical ON recipes(recipe_id) WHERE is_canonical = true;

-- Secondary index: speeds up GET /recipes/{id} ingredients lookup,
-- which was doing a 275K-row seq scan to find a few rows by recipe_id.
CREATE INDEX idx_ingredients_recipe_id ON ingredients(recipe_id);
```

### EXPLAIN After Indexes

```
 Limit  (cost=82399.92..82399.97 rows=20 width=89) (actual time=381.822..381.824 rows=20 loops=1)
   ->  Sort  (cost=82399.92..82524.92 rows=50000 width=89) (actual time=381.821..381.822 rows=20 loops=1)
         Sort Method: top-N heapsort  Memory: 29kB
         ->  GroupAggregate  (cost=2.62..81069.44 rows=50000 width=89) (actual time=0.414..374.312 rows=50000 loops=1)
               Group Key: r.recipe_id
               ->  Incremental Sort  (actual time=0.392..318.521 rows=500002 loops=1)
                     Sort Key: r.recipe_id, rev.review_id
                     Presorted Key: r.recipe_id
                     Full-sort Groups: 13528  Sort Method: quicksort  Average Memory: 28kB
                     ->  Nested Loop Left Join  (actual time=0.131..240.030 rows=500002 loops=1)
                           ->  Nested Loop Left Join  ...
                                 ->  Merge Left Join  (actual time=0.023..63.196 rows=500002 loops=1)
                                       ->  Index Scan using idx_recipes_canonical on recipes r
                                       ->  Index Only Scan using idx_reviews_recipe_covering on reviews rev
                                             Heap Fetches: 0
                                 ->  Memoize (follows lookup, Cache Hits: 490001 / Misses: 10001)
                           ->  Memoize (users lookup, Cache Hits: 490001 / Misses: 10001)
 Execution Time: 381.912 ms
```

**What improved:** The external merge sort to disk (42 MB) is gone. The planner now uses a Merge Left Join between `idx_recipes_canonical` and `idx_reviews_recipe_covering`, both already ordered by `recipe_id`, feeding an Incremental Sort that only needs to sort small groups (28 kB average per group) rather than the entire 500K-row set at once. Most importantly, `Index Only Scan ... Heap Fetches: 0` confirms the covering index allows the planner to read all needed review columns directly from the index without touching the heap. The follows and users joins now use Memoize with a 98% cache hit rate (490K hits vs 10K misses), meaning each distinct user's follow/user row is looked up at most once.

**Final execution time: 381 ms** — down from 401 ms. The improvement is modest in wall-clock terms, but the plan is fundamentally healthier: no disk spills, no seq scans on large tables, and the sort pressure is distributed across 13,528 small in-memory sorts rather than one 42 MB disk-based sort. Under concurrent production load, avoiding disk I/O would compound significantly.

### Ingredient Lookup Improvement (Bonus)

The `idx_ingredients_recipe_id` index also resolved a secondary bottleneck in `GET /recipes/{id}`, where fetching a recipe's ingredients required a full sequential scan of all 275K ingredient rows:

| Query | Before | After |
|-------|--------|-------|
| `SELECT name, quantity FROM ingredients WHERE recipe_id = 1` | 18.8 ms | 3.7 ms |

This is a **5× speedup** on what appears to be a simple point lookup but was actually a full table scan without the index.
