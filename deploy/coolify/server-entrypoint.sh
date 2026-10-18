#!/bin/sh
# Also usable from Coolify's container terminal: figcraft-server-run key
set -eu
: "${FIGCRAFT_PUBLIC_URL:?Set FIGCRAFT_PUBLIC_URL to the public wss://hostname/ backend address}"
figcraft-check-url "$FIGCRAFT_PUBLIC_URL"
umask 077
exec figcraft-server \
    --config /etc/figcraft-server/server.toml \
    --public-url "$FIGCRAFT_PUBLIC_URL" \
    "$@"
