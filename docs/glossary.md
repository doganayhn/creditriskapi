# Financial glossary

These are conceptual definitions, not verified dataset semantics or implemented capabilities.

| Term | Meaning |
| --- | --- |
| Default | Failure to meet an obligation under a specified operational definition; the selected dataset determines this project's label |
| Probability of Default (PD) | Probability of the defined default event over a specified horizon for an eligible population |
| Days Past Due (DPD) | Days a required payment is overdue; not interchangeable with categorical repayment status |
| Delinquency | A payment obligation being overdue; not every delinquency meets a default definition |
| Debt-to-Income (DTI) | Ratio of defined periodic debt obligations to income over a consistent period; exact definitions must be recorded |
| Credit Utilization | Used credit relative to available credit limit, with scope/time and denominator handling specified |
| Exposure at Default (EAD) | Amount exposed when default occurs |
| Loss Given Default (LGD) | Fraction of exposure lost conditional on default, under specified recovery/cost assumptions |
| Expected Loss (EL) | Expected credit loss, commonly represented by PD × LGD × EAD for aligned assumptions/horizon |
| Underwriting | Assessing credit applications under risk, affordability and business policy |
| Credit Score | Numeric representation of creditworthiness whose scale and meaning depend on the methodology |
| Internal Risk Score | Project-defined mapping of risk; not a bureau score and not implemented yet |
| Risk Band | Documented interval/group of risk used for communication or policy |
| Cut-off / Threshold | Probability/score boundary used by policy; temporal cut-off instead means scoring time |
| Approval Rate | Approved applications divided by eligible evaluated applications, with population and period specified |
| Bad Rate | Observed defined bad/default outcomes divided by the specified cohort with mature outcomes |
| Calibration | Agreement between predicted probabilities and observed event frequencies; also a fitted adjustment intended to improve it |
| Scorecard | Structured points-based risk representation, often derived from a statistical model |

`Expected Loss = PD × LGD × EAD` is a conceptual decomposition requiring compatible definitions. Planned V1 primarily models PD. LGD/EAD modeling and expected-loss estimation are not implemented. A raw probability, calibrated probability, internal score and business recommendation remain different quantities.
