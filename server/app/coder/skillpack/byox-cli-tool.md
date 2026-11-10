---
name: byox-cli-tool
description: Build a CLI tool: sub-commands, config, completions
when_to_use: command line tool, cli tool, terminal command, cli app
---
GOAL: a production-ready CLI with --help, sub-commands, config file, and shell completion.

PHASES
1. Argument parsing with cobra (Go) / clap (Rust) / click (Python); print --help.
2. Core action: meaningful errors to stderr; correct POSIX exit codes.
3. Config: ~/.config/<tool>.yaml + env-var overrides (env wins over file).
4. ANSI colour output; TTY detection (disable colour when piped); progress bar.
5. Shell completion (bash/zsh/fish); man page via cobra-man or argparse-manpage.

CORE CONCEPTS
- POSIX: exit 0 = success, 1 = usage error, 2+ = application error.
- TTY check: os.isatty(sys.stdout.fileno()); strip ANSI when piped.
- Config hierarchy: CLI flags > env vars > config file > defaults.

VERIFY: `tool --help` works; `NO_COLOR=1 tool` strips all ANSI; config file read.
