#!/bin/sh
set -eu

# Reuse an existing interpreter. Never bootstrap another Python automatically.
if ! command -v python3 >/dev/null 2>&1; then
    echo 'Python 3.11+ is required. Install it from https://www.python.org/downloads/ and rerun this installer.' >&2
    exit 2
fi
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -f "$script_dir/install.py" ]; then
    exec python3 "$script_dir/install.py" "$@"
fi
echo 'Download install.py alongside this script from the same loc release, then rerun.' >&2
exit 2
