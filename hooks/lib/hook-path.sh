#!/bin/bash
# Shared hook PATH setup. Source it before the hook runs any command.
#
# The Linux agent host keeps its tools in /home/craftagents/bin, so hooks put
# that directory first. On macOS the directory does not exist, and /home is an
# autofs mount: every command lookup through it pays an automount miss. A
# commit-message scan that starts thousands of processes went from 5.8 s to
# 17.7 s and passed its 15 s hook timeout (#1162). Prepend the directory only
# where it exists; the host where it is real keeps the same PATH order.

# ccp_hook_path [dir] -> prepend dir (default /home/craftagents/bin) when it
# is a directory, then export PATH. The argument exists for tests.
ccp_hook_path() {
    local dir="${1:-/home/craftagents/bin}"
    if [[ -d "$dir" ]]; then
        PATH="$dir:$PATH"
    fi
    export PATH
}

ccp_hook_path
