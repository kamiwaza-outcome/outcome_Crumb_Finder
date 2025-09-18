#!/bin/bash
# Simple RFP Import Script
# Usage: ./import.sh [SAM.gov URL]

URL="$1"

if [ -z "$URL" ]; then
    echo "❌ Please provide a SAM.gov URL"
    echo "Usage: ./import.sh https://sam.gov/opp/[noticeId]/view"
    exit 1
fi

echo "🔄 Importing RFP..."
python scripts/import_rfp.py "$URL" --user "shell"

# Send notification to Slack
curl -X POST https://hooks.slack.com/services/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 \
  -H 'Content-Type: application/json' \
  -d "{\"text\": \"✅ Import completed for: $URL\"}" \
  --silent > /dev/null

echo "✅ Done! Check Slack for details."