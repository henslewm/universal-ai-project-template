# Issue #10 review evidence

These are preserved reports for the same pending round-3 opening,
`c759b8ec0ee9f2b8c34e7144f0fe449274619fe053b3ab3009ae52a814e792ca`,
reviewing the implementation at `29422ca`. They are not three review attempts or
an acceptance ledger.

| File | Status |
|---|---|
| `ISSUE_10_ROUND_3.json` | Original local APPROVE, withdrawn by its reviewer after reconsidering a missed requirement. Historical evidence only; do not ingest it or use it to justify acceptance. |
| `ISSUE_10_ROUND_3_EXTERNAL.json` | Unmodified snapshot of the concurrently observed external REJECT_BOUNDED report. Its primary-source omission finding was reproduced; its scope failure uses an invalid `failed_ref`, so offline report validation refuses it. |
| `ISSUE_10_ROUND_3_RECONCILED.json` | Reviewer's corrected REJECT_BOUNDED report, superseding the original local approval within the same opening. Offline validation passes: four of five criteria met, one AC-ADVERSE failure. Not ingested; no acceptance granted. |

The unresolved defect is that a LEGAL_PROPOSITION can validate without any
primary_source_verified validation. Passing the existing 398 tests does not
establish that this requirement is enforced.

See `../ISSUE_10_VALIDATION.md` for the evidence and `../../HANDOFF_CURRENT.md`
for continuation. Preserve the original external report and ledger; reconcile
the pending report, scope and exhausted review-opening budget before resuming.
