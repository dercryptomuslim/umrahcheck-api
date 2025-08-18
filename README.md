# 🚀 UmrahCheck API - Production Ready

## Features
- ✅ Airtable Integration with 100+ Hotels
- ✅ Fixed Field Mapping (works with field names AND IDs)
- ✅ Hotel Recommendations by City & Budget
- ✅ Simulated Live Pricing
- ✅ Commission Tracking Ready

## Endpoints

### Core Endpoints
- `GET /` - API Status
- `GET /health` - Health Check
- `GET /api/hotels` - All Hotels
- `GET /api/airtable/test` - Test Airtable Connection
- `POST /api/customers/recommendations` - Get Hotel Recommendations

### Debug Endpoints
- `GET /api/debug/fields` - See Airtable Field Structure

## Deployment

### Railway
1. Push to GitHub
2. Connect repo to Railway
3. Deploy automatically

### Environment Variables
```
AIRTABLE_API_TOKEN=pat6fC1HtXYcdefn4...
PORT=8080
```

## Frontend Integration
Frontend expects API at:
- Development: http://localhost:8080
- Production: https://umrahcheck-mvp-production.up.railway.app
# Force rebuild: Mon Aug 18 09:35:38 +03 2025
