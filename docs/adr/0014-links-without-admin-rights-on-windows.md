# Links without admin rights on Windows: junctions, and copies with a recorded hash

The kit must run on a Windows workstation without admin rights or Developer Mode, where a symbolic link cannot be made. The tool makes every link through one module: on Linux a symbolic link, relative where it can be; on Windows a directory junction for a folder (`resources/` to the pool, `.claude/skills`), and for a file a copy whose hash is recorded beside it. A copy edited since is kept and reported, never overwritten.

Carried from the workspace template's ADR 0010. Nested inquiries need no links of their own, being clones in place.
