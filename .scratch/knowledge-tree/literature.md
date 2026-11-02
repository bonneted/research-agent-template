# Literature behind the rules

A short review grounding the twelve core rules in the standard literature on research bias, reproducibility, and ML and computational practice. It feeds the README's "Why these rules" section (slice 7).

**How this was checked.** Every reference below was resolved on 2026-11-02 against Crossref by DOI, or against the arXiv API for the papers without a DOI: authors, year, title and venue are verified. What each paper *says* is summarised from prior knowledge of these widely cited works and was **not** re-read against the PDFs (rule 8: these are marked inferences until digested). Before the README quotes a specific number or claim from one of them, check that passage in the source.

## The frame

- **Ioannidis 2005**, *Why most published research findings are false*, PLoS Medicine. [10.1371/journal.pmed.0020124](https://doi.org/10.1371/journal.pmed.0020124). Small effects, flexible designs and selective reporting make most claimed findings likely false. The case for the whole rule set.
- **Munafò et al. 2017**, *A manifesto for reproducible science*, Nature Human Behaviour. [10.1038/s41562-016-0021](https://doi.org/10.1038/s41562-016-0021). Lists the threats across the research cycle and the countermeasures (preregistration, transparency, reporting standards). The closest single reference to our core rules.

## Rule by rule

| Rule | General research | ML / computational |
|---|---|---|
| 1. Explore or confirm, protocol fixed first | Kerr 1998 (HARKing); Simmons, Nelson & Simonsohn 2011 (researcher degrees of freedom); Gelman & Loken 2014 (garden of forking paths); Nosek et al. 2018 (preregistration); Chambers 2013 (registered reports) | Lipton & Steinhardt 2019 (post-hoc explanations presented as hypotheses) |
| 2. Consolidation levels and budget | No direct precedent found: this rule is original to the template. It takes the explore/confirm split of Nosek et al. 2018 and makes the cost of grounding a claim explicit. | — |
| 3. Verification before results | — | Oberkampf & Roy 2010 (verification and validation); Roache 2002 (method of manufactured solutions); Roy & Oberkampf 2011 (the V&V and UQ framework) |
| 4. Every number traces, with its unit | Wilkinson et al. 2016 (FAIR) | Peng 2011; Sandve et al. 2013; Wilson et al. 2014, 2017; Gundersen & Kjensmo 2018; Pineau et al. 2021 (the NeurIPS checklist) |
| 5. No selection on the reported metric | Simmons et al. 2011 | Kaufman et al. 2012 (leakage); Kapoor & Narayanan 2023 (leakage across ML-based science) |
| 6. Uncertainty with every headline number | Wasserstein & Lazar 2016 (the ASA statement on p-values) | Henderson et al. 2018; Dror et al. 2018; Bouthillier et al. 2021; Agarwal et al. 2021; Roy & Oberkampf 2011 |
| 7. A competent baseline | — | Lin 2019 (weak baselines); Melis, Dyer & Blunsom 2018 (well-tuned baselines win); Ferrari Dacrema et al. 2019 (most neural recommenders lose to tuned simple ones) |
| 8. Source claims grounded, inferences marked | Greenberg 2009 (citation distortion creates unfounded authority) | Walters & Wilder 2023 (fabricated citations from ChatGPT) |
| 9. A claim states its scope | Yarkoni 2022 (the generalizability crisis) | Lipton & Steinhardt 2019 (overclaiming) |
| 10. Negative results published | Rosenthal 1979 (the file drawer); Fanelli 2012 (negative results disappearing); Ioannidis 2005 | — |
| 11. The tree never strengthens a claim | No direct precedent verified. The analogy is evidence grading in systematic reviews, where a synthesis is rated no higher than the evidence it pools. Original as a rule for nested inquiries. | — |
| 12. The human confirms, after a blind review | Chambers 2013 (protocol reviewed before data) | Messeri & Crockett 2024 (AI and illusions of understanding); Sharma et al. 2024 (sycophancy: models tell users what they want); Lu et al. 2024 (The AI Scientist, the automation this guards) |

## References

### General research bias

- Chambers, C. D. (2013). Registered Reports: a new publishing initiative at Cortex. *Cortex* 49(3). [10.1016/j.cortex.2012.12.016](https://doi.org/10.1016/j.cortex.2012.12.016)
- Fanelli, D. (2012). Negative results are disappearing from most disciplines and countries. *Scientometrics* 90 (online 2011). [10.1007/s11192-011-0494-7](https://doi.org/10.1007/s11192-011-0494-7)
- Gelman, A., & Loken, E. (2014). The statistical crisis in science. *American Scientist* 102(6). [10.1511/2014.111.460](https://doi.org/10.1511/2014.111.460)
- Greenberg, S. A. (2009). How citation distortions create unfounded authority: analysis of a citation network. *BMJ* 339. [10.1136/bmj.b2680](https://doi.org/10.1136/bmj.b2680)
- Ioannidis, J. P. A. (2005). Why most published research findings are false. *PLoS Medicine* 2(8). [10.1371/journal.pmed.0020124](https://doi.org/10.1371/journal.pmed.0020124)
- Kerr, N. L. (1998). HARKing: hypothesizing after the results are known. *Personality and Social Psychology Review* 2(3). [10.1207/s15327957pspr0203_4](https://doi.org/10.1207/s15327957pspr0203_4)
- Munafò, M. R., Nosek, B. A., Bishop, D. V. M., et al. (2017). A manifesto for reproducible science. *Nature Human Behaviour* 1. [10.1038/s41562-016-0021](https://doi.org/10.1038/s41562-016-0021)
- Nosek, B. A., Ebersole, C. R., DeHaven, A. C., & Mellor, D. T. (2018). The preregistration revolution. *PNAS* 115(11). [10.1073/pnas.1708274114](https://doi.org/10.1073/pnas.1708274114)
- Rosenthal, R. (1979). The file drawer problem and tolerance for null results. *Psychological Bulletin* 86(3). [10.1037/0033-2909.86.3.638](https://doi.org/10.1037/0033-2909.86.3.638)
- Simmons, J. P., Nelson, L. D., & Simonsohn, U. (2011). False-positive psychology: undisclosed flexibility in data collection and analysis allows presenting anything as significant. *Psychological Science* 22(11). [10.1177/0956797611417632](https://doi.org/10.1177/0956797611417632)
- Wasserstein, R. L., & Lazar, N. A. (2016). The ASA statement on p-values: context, process, and purpose. *The American Statistician* 70(2). [10.1080/00031305.2016.1154108](https://doi.org/10.1080/00031305.2016.1154108)
- Wilkinson, M. D., Dumontier, M., Aalbersberg, I. J., et al. (2016). The FAIR guiding principles for scientific data management and stewardship. *Scientific Data* 3. [10.1038/sdata.2016.18](https://doi.org/10.1038/sdata.2016.18)
- Yarkoni, T. (2022). The generalizability crisis. *Behavioral and Brain Sciences* 45 (online 2020). [10.1017/S0140525X20001685](https://doi.org/10.1017/S0140525X20001685)

### Computational science and software

- Oberkampf, W. L., & Roy, C. J. (2010). *Verification and Validation in Scientific Computing*. Cambridge University Press. [10.1017/CBO9780511760396](https://doi.org/10.1017/CBO9780511760396)
- Peng, R. D. (2011). Reproducible research in computational science. *Science* 334(6060). [10.1126/science.1213847](https://doi.org/10.1126/science.1213847)
- Roache, P. J. (2002). Code verification by the method of manufactured solutions. *Journal of Fluids Engineering* 124(1) (online 2001). [10.1115/1.1436090](https://doi.org/10.1115/1.1436090)
- Roy, C. J., & Oberkampf, W. L. (2011). A comprehensive framework for verification, validation, and uncertainty quantification in scientific computing. *Computer Methods in Applied Mechanics and Engineering* 200. [10.1016/j.cma.2011.03.016](https://doi.org/10.1016/j.cma.2011.03.016)
- Sandve, G. K., Nekrutenko, A., Taylor, J., & Hovig, E. (2013). Ten simple rules for reproducible computational research. *PLoS Computational Biology* 9(10). [10.1371/journal.pcbi.1003285](https://doi.org/10.1371/journal.pcbi.1003285)
- Wilson, G., Aruliah, D. A., Brown, C. T., et al. (2014). Best practices for scientific computing. *PLoS Biology* 12(1). [10.1371/journal.pbio.1001745](https://doi.org/10.1371/journal.pbio.1001745)
- Wilson, G., Bryan, J., Cranston, K., et al. (2017). Good enough practices in scientific computing. *PLoS Computational Biology* 13(6). [10.1371/journal.pcbi.1005510](https://doi.org/10.1371/journal.pcbi.1005510)

### Machine learning

- Agarwal, R., Schwarzer, M., Castro, P. S., Courville, A., & Bellemare, M. G. (2021). Deep reinforcement learning at the edge of the statistical precipice. *NeurIPS 2021*. [arXiv:2108.13264](https://arxiv.org/abs/2108.13264)
- Bouthillier, X., Delaunay, P., Bronzi, M., et al. (2021). Accounting for variance in machine learning benchmarks. *MLSys 2021*. [arXiv:2103.03098](https://arxiv.org/abs/2103.03098)
- Dror, R., Baumer, G., Shlomov, S., & Reichart, R. (2018). The hitchhiker's guide to testing statistical significance in natural language processing. *ACL 2018*. [10.18653/v1/P18-1128](https://doi.org/10.18653/v1/P18-1128)
- Ferrari Dacrema, M., Cremonesi, P., & Jannach, D. (2019). Are we really making much progress? A worrying analysis of recent neural recommendation approaches. *RecSys 2019*. [10.1145/3298689.3347058](https://doi.org/10.1145/3298689.3347058)
- Gundersen, O. E., & Kjensmo, S. (2018). State of the art: reproducibility in artificial intelligence. *AAAI 2018*. [10.1609/aaai.v32i1.11503](https://doi.org/10.1609/aaai.v32i1.11503)
- Henderson, P., Islam, R., Bachman, P., Pineau, J., Precup, D., & Meger, D. (2018). Deep reinforcement learning that matters. *AAAI 2018*. [10.1609/aaai.v32i1.11694](https://doi.org/10.1609/aaai.v32i1.11694)
- Kapoor, S., & Narayanan, A. (2023). Leakage and the reproducibility crisis in machine-learning-based science. *Patterns* 4(9). [10.1016/j.patter.2023.100804](https://doi.org/10.1016/j.patter.2023.100804)
- Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in data mining: formulation, detection, and avoidance. *ACM TKDD* 6(4). [10.1145/2382577.2382579](https://doi.org/10.1145/2382577.2382579)
- Lin, J. (2019). The neural hype and comparisons against weak baselines. *ACM SIGIR Forum* 52(2). [10.1145/3308774.3308781](https://doi.org/10.1145/3308774.3308781)
- Lipton, Z. C., & Steinhardt, J. (2019). Troubling trends in machine learning scholarship. *ACM Queue* 17(1). [10.1145/3317287.3328534](https://doi.org/10.1145/3317287.3328534)
- Melis, G., Dyer, C., & Blunsom, P. (2018). On the state of the art of evaluation in neural language models. *ICLR 2018*. [arXiv:1707.05589](https://arxiv.org/abs/1707.05589)
- Pineau, J., Vincent-Lamarre, P., Sinha, K., et al. (2021). Improving reproducibility in machine learning research (a report from the NeurIPS 2019 reproducibility program). *JMLR* 22. [arXiv:2003.12206](https://arxiv.org/abs/2003.12206)

### AI agents in research

- Lu, C., Lu, C., Lange, R. T., Foerster, J., Clune, J., & Ha, D. (2024). The AI Scientist: towards fully automated open-ended scientific discovery. [arXiv:2408.06292](https://arxiv.org/abs/2408.06292)
- Messeri, L., & Crockett, M. J. (2024). Artificial intelligence and illusions of understanding in scientific research. *Nature* 627. [10.1038/s41586-024-07146-0](https://doi.org/10.1038/s41586-024-07146-0)
- Sharma, M., Tong, M., Korbak, T., et al. (2024). Towards understanding sycophancy in language models. *ICLR 2024*. [arXiv:2310.13548](https://arxiv.org/abs/2310.13548)
- Walters, W. H., & Wilder, E. I. (2023). Fabrication and errors in the bibliographic citations generated by ChatGPT. *Scientific Reports* 13. [10.1038/s41598-023-41032-5](https://doi.org/10.1038/s41598-023-41032-5)

## What this changed in the rules (2026-11-02)

- Rule 1: a confirm protocol fixes its analysis, sample size or stopping rule, and the result that would refute the claim (Simmons et al. 2011; Nosek et al. 2018).
- Rule 6: an estimate with its interval, never significance alone (Wasserstein & Lazar 2016; Dror et al. 2018).
- Rule 7: the baseline is tuned with the same budget (Melis et al. 2018; Lin 2019; Ferrari Dacrema et al. 2019).
- Rule 9: a claim about the physical world needs validation, not verification alone (Oberkampf & Roy 2010).
- Rule 10: the denominator is published with the negatives (Gelman & Loken 2014; Lipton & Steinhardt 2019).
- `review-finding`: blind to the user's expectations (Sharma et al. 2024), checklist from Pineau et al. 2021, Kapoor & Narayanan 2023, Roy & Oberkampf 2011.
- `check`: every citekey has an identifier (Walters & Wilder 2023).

## What this changes in the plan

- **README** (slice 7): a "Why these rules" section, one line per rule group with its two or three anchor references, linking this table. Lead with Munafò et al. 2017 and Ioannidis 2005.
- **`AGENTS.md`** (slice 2): no citations in the rules themselves, to keep them short. The guardian may name the bias by its standard name (HARKing, leakage, file drawer), which the README's table explains.
- **Rules 2 and 11 have no standard precedent.** Say so in the README: they are this template's contribution, and should be held to the same scrutiny as the rest.
- Two gaps worth a later look: an evidence-grading reference for rule 11 (the GRADE framework, not verified here), and a units-error case study for rule 4 (the Mars Climate Orbiter mishap report).
