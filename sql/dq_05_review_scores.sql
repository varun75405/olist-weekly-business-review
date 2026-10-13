-- dq_05_review_scores.sql
-- Check: Review scores in raw.raw_reviews outside the valid 1–5 range or null
-- Severity: SOFT (EXCEPTION).
-- Business Reason: Quantify invalid review ratings present in source data prior to staging cleaning.

WITH invalid_reviews AS (
    SELECT
        review_id
    FROM raw.raw_reviews
    WHERE review_score IS NULL
       OR review_score::INT NOT BETWEEN 1 AND 5
)
SELECT
    COUNT(*) AS failing_rows,
    (
        SELECT STRING_AGG(review_id, ', ')
        FROM (SELECT review_id FROM invalid_reviews LIMIT 5) top5
    ) AS sample_ids
FROM invalid_reviews
;
