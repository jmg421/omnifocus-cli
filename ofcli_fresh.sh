#!/bin/bash
# Usage: ./ofcli_fresh.sh [ofcli.py arguments...]
# Only exports if the JSON is older than 1 hour (3600 seconds).

set -e

EXPORT_PATH="data/omnifocus_export.json"
EXPORT_MAX_AGE=3600  # seconds (1 hour)

cd "$(dirname "$0")"

# Check if export is missing or too old
if [ ! -f "$EXPORT_PATH" ] || [ $(( $(date +%s) - $(stat -f %m "$EXPORT_PATH") )) -gt $EXPORT_MAX_AGE ]; then
  echo "Exporting latest OmniFocus data..."
  cd ../OmniFocus-MCP
  npx ts-node src/dumpDatabaseCli.ts
  cd ..
else
  echo "Using existing export: $EXPORT_PATH"
fi

# Run the requested ofcli.py command with fresh data
cd omni-cli
python3 ofcli.py "$@" --file ../data/omnifocus_export.json