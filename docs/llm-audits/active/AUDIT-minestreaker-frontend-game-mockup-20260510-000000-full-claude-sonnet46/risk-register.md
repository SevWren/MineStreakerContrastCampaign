# Risk Register
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

| ID | Risk | Likelihood | Impact | Priority | Mitigation |
|---|---|---|---|---|---|
| R-01 | Game is unplayable in current state (5 critical crashes) | CERTAIN | CRITICAL | P0 | Fix all 5 critical bugs immediately |
| R-02 | Image mode silently falls back to random without error | CERTAIN | HIGH | P0 | Fix API mismatches + improve error logging |
| R-03 | Performance degradation on large boards with many flags | HIGH | HIGH | P1 | Cache ghost surface |
| R-04 | Stale board reference after first-click regeneration | HIGH | MEDIUM | P1 | Store engine reference instead of board |
| R-05 | Dependency version incompatibilities break game | MEDIUM | HIGH | P1 | Create requirements.txt with pinned versions |
| R-06 | Regressions undetectable due to zero test coverage | CERTAIN | HIGH | P1 | Add gameworks test suite |
| R-07 | Win condition doesn't match design spec | CERTAIN | MEDIUM | P2 | Implement flag-check win condition |
| R-08 | Frontend spec not being implemented diverges further from pygame | MEDIUM | MEDIUM | P3 | Document architectural decision |
| R-09 | SA tuning constants drift from last-known-good values | LOW | MEDIUM | P3 | Extract to config file |
| R-10 | PIL CVE in image loading without version pinning | LOW | LOW | P3 | Pin Pillow version |
