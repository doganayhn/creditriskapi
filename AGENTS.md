# Coding-agent instructions

## Project identity
This repository implements a portfolio-quality fintech Credit Risk Scoring & Explainability System.

## Instruction precedence
Current phase prompt > AGENTS.md > PROJECT_RULES.md > PHASE_STATUS.md > ROADMAP.md > docs/ domain and architecture documentation > README.md > implementation. Record meaningful contradictions in the completion report's Risks / Technical Debt section.

## Phase discipline
Exactly ten phases exist. Codex may implement only the explicitly requested phase and must create a completion report after every phase. Reports must accurately disclose tests, limitations, deviations and technical debt. Codex must not automatically start the next phase or create Git commits. The only phase states are NOT_STARTED, IN_PROGRESS and COMPLETED; there is no separate review state.

Each phase follows: phase prompt → Codex implementation → tests → phase completion report → technical review by the project owner. If issues exist, apply fixes and verify them; if no issues remain, the project owner creates the Git commit. The next phase begins only when explicitly requested.

## Required pre-work reading
Before future modifications, read AGENTS.md, PROJECT_RULES.md, ROADMAP.md, PHASE_STATUS.md, relevant docs/, and the most recent phase completion report when available, in that order. Then reconcile these with the current phase prompt using the precedence above.

## Engineering discipline
Preserve reproducibility; avoid hidden global state, machine-specific paths and unnecessary dependencies. Test meaningful behavior. Never fabricate successful tests or dataset properties; report failures honestly. Document deviations. Prefer clear code over excessive abstraction or fake enterprise complexity.

## ML discipline
Never fit preprocessing on full datasets, leak target/future information, or claim temporal validation unsupported by the data. Raw probabilities are not automatically calibrated PD. Do not claim SHAP sums to calibrated probability unless mathematically supported. Keep business policy separate from training.

## Documentation discipline
After each phase, update documentation to match actual implementation, preserve previous reports, and create a new immutable completion report. Never claim unfinished functionality exists or rewrite history to hide limitations. Explicit correction addenda preserve the original report and review outcome.
