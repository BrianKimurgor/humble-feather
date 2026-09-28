# Plan

Ordered steps from here to a submitted model. Each step is completed and
verified before the next one starts.

## 1. Validation strategy (in progress)

Define, in code, how we measure "is this model good" -- before any model
exists. Ranking data is Jan + Jul 2026; training data is all of 2025. A
random row split would hide how badly a model generalizes across time, so
validation holds out whole months instead:

- **Fold "jan"**: train on Feb-Dec 2025, validate on Jan 2025 (stands in for
  ranking Jan 2026).
- **Fold "jul"**: train on all months except Jul 2025, validate on Jul 2025
  (stands in for ranking Jul 2026).

RMSE tracked overall and per `monitored_airport`, since airports behave
differently (confirmed during the data audit).

Deliberately out of scope here: whether flagged rows (see
`docs/data_dictionary.md`) are included or excluded from training. That is
step 2, a row-filtering *policy* decision, kept separate from the
time-based split *mechanism* built in this step.

## 2. Decide how flags feed into training (decided 2026-09-21)

**Decision: use all rows as-is. No row filtering by any flag in training.**

The clean database never drops rows (see `src/clean.py`); this decision
confirms training itself also does not filter on `flag_taxitime_nonpositive`,
`flag_taxitime_gt_3h`, `flag_taxitime_gt_24h`, or `flag_flt_unmatched` --
every departure row in `movements` is used to fit the model. Considered
and rejected: excluding the physically-impossible non-positive rows only,
or excluding all flagged rows. Revisit if error analysis on the baseline
or a real model shows these rows are actively hurting validation RMSE
(Root Mean Square Error) -- in particular Rome-Fiumicino Airport (LIRF),
which showed 2-3x the error of every other airport in the naive baseline
check, correlated with its cluster of extreme-taxi-time rows.

## 3. Baseline model (done 2026-09-21)

Median taxi-out per `monitored_airport`. Not meant to be accurate -- meant
to prove the full round-trip works: fill `submitting.parquet`, upload as
`humble-feather_v1.parquet`, confirm a result file appears in the team
bucket. Safety net before anything fancier.

**Result: succeeded.** `humble-feather_v1.parquet` scored **RMSE (Root
Mean Square Error) = 668.335 seconds** on all 344,841 departures (full
`used_pairs` match, nothing rejected). Pipeline: `src/train.py` (per-airport
medians) -> `src/predict.py` (applies them to `ranking`) -> `src/submit.py`
(validates against the template, writes, uploads). Our own validation
estimate from step 1 (610.5s on the Jan fold, 754.0s on the Jul fold) was in
the right ballpark versus this real score -- a good sign the validation
strategy is trustworthy, not wildly optimistic or pessimistic. This score
is now the floor every future model must beat.

## 4. Feature engineering and a real model

LightGBM first, informed by where the baseline's errors actually are
(per-airport, per-hour, etc.). Not started until 1-3 are done.
