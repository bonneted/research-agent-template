# uq-reliability

For a study that propagates uncertainty or estimates a probability of failure: Monte Carlo and its variants, FORM and SORM, surrogates, sensitivity indices.

1. **Estimator convergence shown**: the coefficient of variation of the estimated probability of failure (or of the estimated quantity), and its confidence interval, against the number of samples.
2. **Sample size justified** beforehand: from the target coefficient of variation and the order of the probability, stated in the protocol.
3. **Distributions and their sources stated**: each random variable's distribution, parameters and correlation, with the source of each (a page of a standard, a dataset with its sha256, a paper's table), or marked as assumed.
4. **Surrogate validated** on held-out points not used to build or tune it, with its error stated in the region that matters (near the limit state for a reliability estimate), and that error carried into the result.
5. **FORM or SORM checked against sampling** at least once in the study, on a case where the sampling estimate is affordable, with the difference stated.
6. **Sensitivity indices with their estimator error** (bootstrap or repeated estimates), and the sample size behind them.
