# ml-training

For a study that trains networks (physics-informed or not) and compares them, with each other or with a classical method. Taken as they are from the study rules of the spimat workspace (its rules 2, 4–6, 9 and 10), written there for scientific ML in mechanics: rules 5 and 6 below name mechanics quantities and FEM, read them for your problem's own.

1. Each comparison is attributable to its declared factors: one factor by default, a small factorial (2×2) when an interaction is the hypothesis.
2. No selection on the reported error: settings chosen on a calibration case separate from evaluation; always report the final iterate. A stabilised estimator (e.g. median over the last 10% of logged steps) may be the headline if declared beforehand and computed only from quantities available in practice; the final iterate is reported beside it.
3. Tuning: the phase states its policy; default is an equal learning-rate sweep per arm. Budget: state the matched axis (params / steps / wall-clock), report all three plus GPU type.
4. Seeds: one seed controls init and collocation; arms paired by seed; report median and full range; 3 to screen, 5 to claim; effect rule = beyond both the reference floor and the seed spread.
5. Reporting: primary metric declared per study; always report equilibrium/traction residuals on an independent grid, engineering quantities (Kt, peak stress, reaction, identified parameters), energy-norm error where a reference exists; area-weighted scoring grids.
6. Against FEM: same constitutive implementation (shared material library); compare at matched accuracy; competent solver, hardware on both sides stated; count the whole cost (training is the solve); inverse problems compare against FEMU.
