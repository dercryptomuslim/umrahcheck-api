#!/bin/bash
# Deploy RapidAPI Integration to Railway

echo "🚀 Deploying RapidAPI Integration to Railway..."

# Set environment variables
echo "📝 Setting environment variables..."
railway variables --set "RAPIDAPI_KEY=05f220e835mshcb428f0416e1b90p148a1ajsn1a4eec316e79"
railway variables --set "USE_RAPIDAPI=true"

# Commit and push changes
echo "📦 Committing changes..."
git add rapidapi_booking_apidojo.py umrahcheck_api_fixed.py
git commit -m "Integrate RapidAPI as primary hotel price source

- Add BookingApiDojo class for reliable API-based pricing
- Update /api/hotels/scrape-prices endpoint with RapidAPI primary, Playwright fallback
- Use official Booking.com API via apidojo-booking-v1 endpoints
- Support customer-specific dates and parameters (adults, rooms, children)
- Format results to match existing API structure
- Add comprehensive error handling with graceful fallback
- Update API stats to reflect RapidAPI integration

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Deploy to Railway
echo "🚂 Deploying to Railway..."
railway deploy

echo "✅ Deployment complete!"
echo ""
echo "🔧 Environment Variables Set:"
echo "  RAPIDAPI_KEY=05f22...79 (masked)"
echo "  USE_RAPIDAPI=true"
echo ""
echo "📋 New Features:"
echo "  • RapidAPI integration with Booking.com"
echo "  • Playwright fallback for reliability"
echo "  • Real hotel prices with customer dates"
echo "  • Improved API response format"
echo ""
echo "🧪 Test the integration:"
echo "  curl -X POST https://YOUR_RAILWAY_URL/api/hotels/scrape-prices \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"hotel_name\": \"Swissôtel Al Maqam Makkah\", \"city\": \"Makkah\", \"checkin_date\": \"2025-09-15\", \"checkout_date\": \"2025-09-20\"}'"