# Links without admin rights on Windows: junctions, and copies with a recorded hash

The workspace must run on a Windows workstation without admin rights or Developer Mode, where a symbolic link cannot be made. `ws` makes every link through one module (`tools/ws/links.py`): on Linux a symbolic link, relative where it can be; on Windows a directory junction for a folder (the pool link, the skills, `.claude/skills`, the study mounts), which needs no rights and holds an absolute path; and for a file (the off-limits hook) a copy, whose hash is recorded beside it when `ws` writes it. A copy left as `ws` wrote it follows the hub's file; a copy edited since is kept and reported, never overwritten. A `.claude/skills` link a repository commits, which git checks out on Windows as a text file, is replaced by a junction and marked `skip-worktree`.

## Considered options

- **Require Developer Mode.** Rejected: the workstation is managed, and the user has no admin rights.

## Consequences

Linux behaviour is unchanged. The Windows path is tested on Linux by standing in for the platform and the junction primitives. A workspace that moves on Windows must be synced again, its junctions being absolute.
