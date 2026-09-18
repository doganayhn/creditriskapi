# Descriptive TEST subgroup diagnostics

Demographic variables are not model inputs. The existing TEST split supplies an aligned separate review frame; no heuristic reconstruction or relabeling was used. Sex, age, education and marital status retain literal numeric values, including individual ages. Education 0/5/6 and marital status 0 have undocumented meanings; no new meanings are assigned.

Minimum count is 100. Smaller groups retain only field, value, count and insufficient-sample status; all metrics are unavailable. For a sufficiently large single-class group, AUC is undefined while Brier, mean probability and observed rate remain mathematically available. Calibration gap is mean PD minus observed rate. No lending threshold is applied to subgroups.

This is historical Taiwan credit-card data from 2005. These are aggregate descriptive validation diagnostics, not causal claims, a fairness ranking, a conclusion that the model is fair/discriminatory, or a legal/regulatory assessment. Multiple noisy subgroup estimates and proxy effects require caution. Modern deployment would need jurisdiction-specific governance. No model change resulted from these diagnostics.

| field | raw_value | count | status | observed_default_rate | mean_reported_probability | roc_auc | brier_score | calibration_gap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sex | 1 | 1766 | sufficient | 0.25368063 | 0.22875153 | 0.75223553 | 0.15556906 | -0.024929107 |
| sex | 2 | 2734 | sufficient | 0.20043892 | 0.21605524 | 0.79995709 | 0.12200373 | 0.015616326 |
| age | 21 | 6 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 22 | 76 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 23 | 127 | sufficient | 0.23622047 | 0.28127504 | 0.8161512 | 0.14023319 | 0.045054571 |
| age | 24 | 174 | sufficient | 0.27586207 | 0.27506376 | 0.8139881 | 0.14016974 | -0.00079830864 |
| age | 25 | 177 | sufficient | 0.25988701 | 0.25238605 | 0.80625622 | 0.13898829 | -0.0075009552 |
| age | 26 | 189 | sufficient | 0.21693122 | 0.23688229 | 0.82053395 | 0.12897909 | 0.019951069 |
| age | 27 | 215 | sufficient | 0.22325581 | 0.21766354 | 0.73958333 | 0.14425571 | -0.0055922747 |
| age | 28 | 203 | sufficient | 0.18226601 | 0.22351706 | 0.7827255 | 0.11803229 | 0.041251046 |
| age | 29 | 247 | sufficient | 0.18218623 | 0.19209623 | 0.82970297 | 0.11128853 | 0.0099099982 |
| age | 30 | 202 | sufficient | 0.21782178 | 0.20627187 | 0.81228423 | 0.13177121 | -0.011549916 |
| age | 31 | 187 | sufficient | 0.18716578 | 0.19983356 | 0.67359023 | 0.14004302 | 0.012667788 |
| age | 32 | 171 | sufficient | 0.19298246 | 0.18327316 | 0.81598595 | 0.12072317 | -0.0097092941 |
| age | 33 | 173 | sufficient | 0.14450867 | 0.19508299 | 0.73945946 | 0.11105562 | 0.050574319 |
| age | 34 | 184 | sufficient | 0.17934783 | 0.20192892 | 0.82239615 | 0.10609651 | 0.022581099 |
| age | 35 | 159 | sufficient | 0.19496855 | 0.20922794 | 0.79196069 | 0.1267778 | 0.014259384 |
| age | 36 | 165 | sufficient | 0.25454545 | 0.20241742 | 0.74061169 | 0.14965179 | -0.052128036 |
| age | 37 | 167 | sufficient | 0.20958084 | 0.19961957 | 0.84253247 | 0.12380784 | -0.0099612679 |
| age | 38 | 150 | sufficient | 0.20666667 | 0.20477877 | 0.76931418 | 0.13871415 | -0.001887898 |
| age | 39 | 142 | sufficient | 0.24647887 | 0.22381628 | 0.75901202 | 0.15027106 | -0.022662596 |
| age | 40 | 130 | sufficient | 0.22307692 | 0.22648949 | 0.71969956 | 0.14442285 | 0.0034125694 |
| age | 41 | 129 | sufficient | 0.17829457 | 0.21517555 | 0.7337982 | 0.12962565 | 0.036880975 |
| age | 42 | 109 | sufficient | 0.28440367 | 0.22749067 | 0.83788255 | 0.14915934 | -0.056912997 |
| age | 43 | 96 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 44 | 111 | sufficient | 0.21621622 | 0.21299092 | 0.70019157 | 0.14335916 | -0.0032252962 |
| age | 45 | 79 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 46 | 97 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 47 | 83 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 48 | 76 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 49 | 65 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 50 | 63 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 51 | 59 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 52 | 40 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 53 | 42 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 54 | 50 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 55 | 36 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 56 | 29 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 57 | 22 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 58 | 11 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 59 | 16 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 60 | 8 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 61 | 6 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 62 | 8 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 63 | 1 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 64 | 4 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 65 | 6 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 66 | 3 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 67 | 1 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 68 | 2 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 69 | 1 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 70 | 1 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 71 | 1 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| age | 75 | 1 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| education | 1 | 1580 | sufficient | 0.20253165 | 0.19477173 | 0.77720734 | 0.1269519 | -0.0077599154 |
| education | 2 | 2086 | sufficient | 0.22866731 | 0.23404389 | 0.79125412 | 0.13640149 | 0.0053765857 |
| education | 3 | 766 | sufficient | 0.25718016 | 0.24759108 | 0.74228096 | 0.15814449 | -0.0095890735 |
| education | 4 | 20 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| education | 5 | 40 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| education | 6 | 8 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| marital_status | 0 | 8 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
| marital_status | 1 | 2063 | sufficient | 0.24139603 | 0.21974795 | 0.78338081 | 0.14076499 | -0.021648071 |
| marital_status | 2 | 2383 | sufficient | 0.20520352 | 0.22109909 | 0.77927391 | 0.13049274 | 0.015895563 |
| marital_status | 3 | 46 | insufficient_sample | unavailable | unavailable | unavailable | unavailable | unavailable |
