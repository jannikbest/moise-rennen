#!/usr/bin/env bash
# Back-compat alias — use ./dev.sh
exec "$(cd "$(dirname "$0")" && pwd)/dev.sh" "$@"
