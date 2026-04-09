-- Add cost_usd to scan_reports so the dashboard can surface per-scan spend.
-- Backfills from credit_transactions where a matching usage row references
-- the scan via scan_id (added in 20260308200000_balance_usd.sql).
--
-- Note: idx_scan_reports_user_created already exists from
-- 20260317100000_pagination_indexes.sql, so no new index is created here.

ALTER TABLE public.scan_reports
    ADD COLUMN IF NOT EXISTS cost_usd NUMERIC(10, 4);

-- Backfill: for each scan, sum the absolute amount of its 'usage' transactions.
-- Usage amounts are stored as negatives (see deduct_balance), so we negate.
UPDATE public.scan_reports sr
   SET cost_usd = sub.total
  FROM (
        SELECT scan_id, ROUND(SUM(-amount)::numeric, 4) AS total
          FROM public.credit_transactions
         WHERE type = 'usage'
           AND scan_id IS NOT NULL
         GROUP BY scan_id
       ) sub
 WHERE sr.id = sub.scan_id
   AND sr.cost_usd IS NULL;
