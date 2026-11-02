# Links without admin rights on Windows: junctions

The kit must run on a Windows workstation without admin rights or Developer Mode, where a symbolic link cannot be made. The tool makes every link through one module: on Linux a symbolic link, relative where it can be; on Windows a directory junction for a folder (`resources/` to the pool, `.claude/skills`), which needs no rights and holds an absolute path.

Carried from the workspace template's ADR 0010. Nested inquiries need no links of their own, being clones in place.
