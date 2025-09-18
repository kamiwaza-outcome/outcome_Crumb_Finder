#!/bin/bash

# RFP Discovery System - Daily Run Script
# Run this script to execute the enhanced RFP discovery

echo "======================================================================"
echo "🚀 RFP DISCOVERY SYSTEM - DAILY RUN"
echo "======================================================================"
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Check for required environment variables
if [ -z "$GOOGLE_SHEETS_CREDS_PATH" ]; then
    echo "❌ ERROR: GOOGLE_SHEETS_CREDS_PATH not set"
    echo "   Please run: export GOOGLE_SHEETS_CREDS_PATH=/path/to/your/credentials.json"
    exit 1
fi

if [ -z "$SAM_API_KEY" ]; then
    echo "❌ ERROR: SAM_API_KEY not set"
    echo "   Please run: export SAM_API_KEY=your_sam_api_key"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY not set"
    echo "   Please run: export OPENAI_API_KEY=your_openai_api_key"
    exit 1
fi

echo "✅ Environment variables configured"
echo ""

# Check if credentials file exists
if [ ! -f "$GOOGLE_SHEETS_CREDS_PATH" ]; then
    echo "❌ ERROR: Credentials file not found at: $GOOGLE_SHEETS_CREDS_PATH"
    exit 1
fi

echo "✅ Google credentials file found"
echo ""

# Install required dependencies if needed
echo "📦 Checking dependencies..."
pip list | grep -q psutil || pip install psutil
pip list | grep -q tenacity || pip install tenacity
pip list | grep -q google-api-python-client || pip install google-api-python-client
pip list | grep -q google-auth || pip install google-auth
echo "✅ Dependencies ready"
echo ""

# Run the enhanced discovery
echo "🔍 Starting RFP discovery..."
echo "======================================================================"
echo ""

python enhanced_discovery.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================================"
    echo "✨ Discovery completed successfully!"
    echo "======================================================================"
    
    # Show metrics if file exists
    if [ -f "discovery_metrics.json" ]; then
        echo ""
        echo "📊 Metrics Summary:"
        python -c "import json; m=json.load(open('discovery_metrics.json')); print(f\"  • RFPs Searched: {m['processing_metrics']['total_searched']}\"); print(f\"  • Qualified: {m['processing_metrics']['qualified']}\"); print(f\"  • Estimated Cost: \${m['estimated_costs']['total_usd']}\")" 2>/dev/null || echo "  (Metrics file available at discovery_metrics.json)"
    fi
else
    echo ""
    echo "======================================================================"
    echo "⚠️ Discovery completed with warnings or errors"
    echo "   Check logs/rfp_discovery.log for details"
    echo "======================================================================"
fi

echo ""
echo "📂 View results at:"
echo "   • Qualified: https://docs.google.com/spreadsheets/d/$SPREADSHEET_ID"
echo "   • Maybe: https://docs.google.com/spreadsheets/d/$MAYBE_SPREADSHEET_ID"
echo "   • All RFPs: https://docs.google.com/spreadsheets/d/$SPAM_SPREADSHEET_ID"
echo ""