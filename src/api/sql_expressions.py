"""Reusable SQL fragments for derived values (3NF: computed at read time)."""

# Per-review z-score from that reviewer's full rating history.
Z_SCORE_EXPR = """
CASE
    WHEN user_stats.review_count < 1
      OR user_stats.stddev IS NULL
      OR user_stats.stddev = 0
    THEN 0.0
    ELSE (rev.raw_score - user_stats.mean) / user_stats.stddev
END
"""

USER_STATS_LATERAL = """
LEFT JOIN LATERAL (
    SELECT
        AVG(r2.raw_score) AS mean,
        STDDEV(r2.raw_score) AS stddev,
        COUNT(*)::int AS review_count
    FROM reviews r2
    WHERE r2.user_id = rev.user_id
) user_stats ON true
"""

# trust_weight is not persisted for scoring; default relationship weight = 1.0
TRUST_WEIGHT_EXPR = "1.0"

TRUST_AUTHORITY_SUBQUERY = """
COALESCE((
    SELECT AVG(ABS(z_val))
    FROM (
        SELECT
            CASE
                WHEN s.cnt < 1 OR s.stddev IS NULL OR s.stddev = 0 THEN 0.0
                ELSE (r.raw_score - s.mean) / s.stddev
            END AS z_val
        FROM reviews r
        CROSS JOIN LATERAL (
            SELECT
                AVG(r2.raw_score) AS mean,
                STDDEV(r2.raw_score) AS stddev,
                COUNT(*)::int AS cnt
            FROM reviews r2
            WHERE r2.user_id = r.user_id
        ) s
        WHERE r.user_id = u.user_id
    ) computed
), 0.0)
"""
