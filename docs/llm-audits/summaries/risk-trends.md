# Risk Trends

## Audit Run History

| Date | Audit ID | Critical | High | Medium | Low | Risk Score |
|---|---|---|---|---|---|---|
| 2026-05-10 | AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46 | 5 | 8 | 7 | 4 | CRITICAL |

## Trend Notes

This is the first audit of the `gameworks/` package on this branch. The critical risk score reflects that **the game cannot currently complete a single session** due to runtime crashes. All 5 critical bugs are straightforward fixes requiring < 1 hour of work.

After Phase 0 fixes, expected risk score: HIGH (performance and test coverage gaps remain).
After Phase 1-3 fixes, expected risk score: MEDIUM.
