# Studies pin the library by commit, and every run stamps what it used

A study depends on the library through a git commit pinned in its `pyproject.toml`, not through an editable install of a sibling checkout, and every run records the library install it actually resolved. With an editable install, switching the library checkout's branch silently changes what every study measures, and a result stops being tied to the code that produced it. The stamp, not the pin, is the evidence: an editable install used while developing a library change is detected rather than trusted.

Taken from the spimat workspace (its ADR 0002). The library is named by the manifest; the stamp asks it for `installed_from()` when it has one, and otherwise reads its distribution's metadata (PEP 610), with the commit and state of an editable checkout.

## Consequences

Moving the library's pin is a recorded deviation in any running protocol, and it triggers the study's canary runs. A workspace without a library spawns studies with no pin.
