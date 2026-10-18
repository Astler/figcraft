#!/bin/sh
# Accept a root WSS URL only. Reject credentials/keys before they reach a web build.
set -eu
url=${1:-}
fail() {
    echo "FIGCRAFT_PUBLIC_URL must be wss://hostname/ (optional public port; no key, query, path, or whitespace)." >&2
    exit 1
}
case "$url" in
    ''|*[!A-Za-z0-9.:/-]*) fail ;;
esac
printf '%s\n' "$url" | LC_ALL=C grep -Eq '^wss://[A-Za-z0-9][A-Za-z0-9.-]*(:[0-9]{1,5})?/$' || fail
