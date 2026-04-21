# Saturation Winner Visual Acceptance Checklist

Use this checklist during Phase 7 before setting `user_approved=yes` in `winner_visual_review.csv`.

## Review Inputs
- `metrics_*.json` for each candidate.
- `visual_*.png` for each candidate.
- Candidate rank context (why this candidate is currently top-ranked by metrics).

## Pass/Fail Criteria
Mark each line `pass` or `fail`. If any required line fails, reject the candidate and record a reason.

- Required: grid geometry is coherent (no obvious warped board structure or catastrophic cell deformation).
- Required: mine/number reconstruction appears internally consistent without broad artifact regions.
- Required: no large blotchy or smeared zones that hide board semantics.
- Required: edge and corner regions are not visibly broken relative to interior quality.
- Required: output is not materially worse than the next-best candidate in obvious visual defects.
- Required: visual quality is acceptable for reporting and downstream documentation refresh.

## Rejection Reasons (Plain English)
Use one short reason in `rejection_reason`:
- `severe smear artifacts`
- `geometry distortion`
- `edge collapse`
- `inconsistent board semantics`
- `unacceptable quality vs alternate candidate`

## Approval Logging Rules
- Reviewer is you; your decision is authoritative.
- Set `user_approved=yes` only when all required criteria pass.
- For a reject, set `user_approved=no` and provide `rejection_reason`.
- Always fill `reviewer` and `reviewed_at_utc`.

## Decision Rule
- A candidate cannot be promoted on metrics alone.
- Promotion requires both:
  - metric eligibility from the run matrix gates, and
  - visual approval from this checklist.
