# literature-check

For an inquiry that checks the claims of published papers against competent practice, one paper at a time. Modelled on how the spimat workspace's claim checker works (`spimat-pinn-claims`, "How a paper is checked").

1. **Claim register.** Read the paper with its claims as lenses. Each claim is a row of the inquiry's register: its quotation and page, its metric, the published number, and a verdict, one of `holds | tie | fails | untestable as published`. A verdict needs the phase and runs behind it.
2. **Reproduce the paper's own baseline** before testing its claim, when it reports one, to the precision it reports. A baseline that cannot be reproduced is a finding in itself.
3. **The inquiry does not win by changing the problem.** The paper's case, parameterisation and data come first; a variant (more noise, another mesh, a prior) goes beside it as its own arm, never in its place.
4. **Code and data availability checked and recorded** at the start: the paper's data statement, the authors' repositories, Zenodo. Public code rerun is an arm, logged as a deviation if added later; numbers not rerun are cited from the paper, and every comparison says so.
5. **Each paper's protocol is written before its first run**: its section of `PLAN.md` fixes the claims tested, the arms and their settings, the metric and the budget.
