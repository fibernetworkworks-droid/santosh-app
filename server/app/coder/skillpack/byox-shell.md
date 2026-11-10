---
name: byox-shell
description: Build a Unix shell: fork/exec, pipes, redirects, job control
when_to_use: unix shell, own bash, terminal shell, command shell from scratch
---
GOAL: a shell that runs pipelines, redirects I/O and supports background jobs.

PHASES
1. REPL: read line, tokenise, fork() + execvp(); wait for child; repeat.
2. Built-ins: cd, exit, export; PATH lookup for commands.
3. Pipelines: ls | grep | wc — N-stage pipe chain via pipe(2) + dup2.
4. Redirects: < infile, > outfile, >> append, 2>&1 (dup2 fd wiring).
5. Job control: Ctrl-Z (SIGTSTP), bg, fg, background &, SIGCHLD handler.

CORE CONCEPTS
- fork() returns child PID to parent, 0 to child; exec() replaces child image.
- Pipe: pipe(fds); child: dup2(fds[1], STDOUT_FILENO); parent: read fds[0].
- Job control: setpgid(pid, pid) puts child in its own process group; tcsetpgrp gives it the terminal.

LANGUAGE: C (POSIX) for correctness; Go for learning without pointer management.

VERIFY: `ls -la | grep ".c" | wc -l` works; Ctrl-Z suspends; fg resumes.
