# 🚀 RFP Discovery + Kamiwaza Quick Start

## Prerequisites
- Docker Desktop installed and running
- Kamiwaza platform running locally (port 7777)
- SAM.gov API key
- Google Sheets credentials (optional)

## 1. Configuration (2 minutes)

Create `.env` file in `app_garden_template/backend/`:
```bash
# Kamiwaza (local models)
KAMIWAZA_ENDPOINT=http://localhost:7777/api/

# SAM.gov (required)
SAM_API_KEY=your-sam-api-key-here

# Google Sheets (optional)
SPREADSHEET_ID=your-sheet-id
GOOGLE_SHEETS_CREDS_PATH=credentials.json
```

## 2. Start System (1 minute)

```bash
cd app_garden_template
docker-compose up
```

Wait for:
- ✅ Backend: http://localhost:8000
- ✅ Frontend: http://localhost:3000

## 3. Access Dashboard

Open browser: http://localhost:3000/rfp

## 4. Run First Discovery

1. **Select Model**: Choose from available Kamiwaza models
2. **Set Batch Size**: Start with 10 for testing
3. **Click**: "Run Discovery Now"

## 5. Monitor Progress

Watch real-time:
- Progress bar showing RFPs processed
- Qualified/Maybe/Rejected counts
- Live logs

## Quick Test Commands

```bash
# Check daemon status
curl http://localhost:8000/api/rfp/daemon/status

# Trigger discovery via API
curl -X POST http://localhost:8000/api/rfp/discover/background \
  -H "Content-Type: application/json" \
  -d '{"model_name": "llama-3.1-70b", "batch_size": 5, "max_rfps": 20}'

# View recent RFPs
curl http://localhost:8000/api/rfp/recent?limit=10
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No models available" | Ensure Kamiwaza is running on port 7777 |
| "SAM.gov error" | Check SAM_API_KEY in .env |
| "Cannot connect to daemon" | Backend may still be starting, wait 30s |
| "WebSocket disconnected" | Normal if no active runs, will reconnect |

## Next Steps

1. **Setup Schedule**: Click "Setup 5PM Daily Schedule" in UI
2. **Configure Company**: Edit `company_config.json`
3. **Add Past RFPs**: Update `data/winning_rfps.txt`
4. **Production Deploy**: See `docs/RFP_DISCOVERY_INTEGRATION.md`

## Success Indicators

✅ Daemon shows "Running" in UI
✅ Models dropdown populated
✅ Discovery runs show progress
✅ RFPs appear in table
✅ Logs visible in viewer

---
**Ready!** Your RFP Discovery System is now using local Kamiwaza models instead of OpenAI 🎉