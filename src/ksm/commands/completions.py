"""Completions command for ksm.

Handles `ksm completions <shell>` — generates shell completion
scripts for bash, zsh, and fish.

Requirements: 21.1, 21.2, 21.3
"""

import argparse
import sys

from ksm.errors import format_error

_BASH_COMPLETION = """\
_ksm_completions() {
    local cur prev commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    commands="add ls sync rm registry init info search completions"

    case "$prev" in
        ksm)
            COMPREPLY=( $(compgen -W "$commands" -- "$cur") )
            ;;
        registry)
            COMPREPLY=( $(compgen -W "add ls rm inspect" -- "$cur") )
            ;;
        completions)
            COMPREPLY=( $(compgen -W "bash zsh fish" -- "$cur") )
            ;;
    esac
}
complete -F _ksm_completions ksm
"""

_ZSH_COMPLETION = """\
#compdef ksm

_ksm() {
    local -a commands
    commands=(
        'add:Install a bundle'
        'ls:List installed bundles'
        'sync:Sync installed bundles'
        'rm:Remove an installed bundle'
        'registry:Manage registries'
        'init:Initialise .kiro/ directory'
        'info:Show bundle information'
        'search:Search for bundles'
        'completions:Generate shell completions'
    )

    _arguments -C \\
        '--version[Show version]' \\
        '1:command:->cmd' \\
        '*::arg:->args'

    case "$state" in
        cmd)
            _describe 'command' commands
            ;;
        args)
            case "$words[1]" in
                registry)
                    local -a subcmds
                    subcmds=(
                        'add:Add a registry'
                        'ls:List registries'
                        'rm:Remove a registry'
                        'inspect:Inspect a registry'
                    )
                    _describe 'subcommand' subcmds
                    ;;
                completions)
                    _values 'shell' bash zsh fish
                    ;;
            esac
            ;;
    esac
}

_ksm "$@"
"""

_FISH_COMPLETION = """\
# ksm completions for fish
set -l commands add ls sync rm registry init info search completions
set -l reg_cmds add ls rm inspect

complete -c ksm -f
complete -c ksm -n "not __fish_seen_subcommand_from $commands" -a add -d 'Install a bundle'
complete -c ksm -n "not __fish_seen_subcommand_from $commands" -a ls -d 'List installed bundles'
complete -c ksm -n "not __fish_seen_subcommand_from $commands" -a sync -d 'Sync installed bundles'
complete -c ksm -n "not __fish_seen_subcommand_from $commands" -a rm -d 'Remove an installed bundle'
complete -c ksm -n "not __fish_seen_subcommand_from $commands" -a registry -d 'Manage registries'
complete -c ksm -n "not __fish_seen_subcommand_from $commands" -a init -d 'Initialise .kiro/ directory'
complete -c ksm -n "not __fish_seen_subcommand_from $commands" -a info -d 'Show bundle information'
complete -c ksm -n "not __fish_seen_subcommand_from $commands" -a search -d 'Search for bundles'
complete -c ksm -n "not __fish_seen_subcommand_from $commands" -a completions -d 'Generate shell completions'
complete -c ksm -n "__fish_seen_subcommand_from registry; and not __fish_seen_subcommand_from $reg_cmds" -a "$reg_cmds"
complete -c ksm -n "__fish_seen_subcommand_from completions" -a "bash zsh fish"
"""  # noqa: E501

_SCRIPTS: dict[str, str] = {
    "bash": _BASH_COMPLETION,
    "zsh": _ZSH_COMPLETION,
    "fish": _FISH_COMPLETION,
}


def run_completions(args: argparse.Namespace) -> int:
    """Print shell completion script. Returns exit code."""
    shell: str = args.shell

    script = _SCRIPTS.get(shell)
    if script is None:
        print(
            format_error(
                f"Unsupported shell '{shell}'.",
                "Supported: bash, zsh, fish",
                "Example: ksm completions bash",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return 1

    print(script)
    return 0
