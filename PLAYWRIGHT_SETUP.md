# 🎭 Playwright Integration for UmrahCheck

Real-time hotel price scraping using Playwright web automation.

## Features

- ✅ Real-time price scraping from Booking.com and Hotels.com
- ✅ Parallel scraping from multiple platforms
- ✅ Automatic fallback to simulation if scraping fails
- ✅ Sentry integration for error tracking
- ✅ Performance monitoring for scraping operations
- ✅ Headless browser operation for server deployment

## Environment Variables

```bash
# Enable Playwright scraping (default: false)
ENABLE_PLAYWRIGHT=true

# Other existing variables
AIRTABLE_API_TOKEN=your_token
AIRTABLE_BASE_ID=your_base_id
AIRTABLE_TABLE_ID=your_table_id
```

## API Endpoints

### 1. Live Prices with Playwright (when enabled)
```bash
POST /api/hotels/live-prices
{
  "hotel_name": "Swissôtel Al Maqam Makkah",
  "city": "Makkah",
  "checkin_date": "2024-03-01",
  "checkout_date": "2024-03-05"
}
```

### 2. Direct Scraping Endpoint
```bash
POST /api/hotels/scrape-prices
{
  "hotel_name": "Conrad Makkah",
  "city": "Makkah", 
  "checkin_date": "2024-03-01",
  "checkout_date": "2024-03-05"
}
```

Response:
```json
{
  "status": "success",
  "data": {
    "hotel_name": "Conrad Makkah",
    "city": "Makkah",
    "results": [
      {
        "platform": "Booking.com",
        "price": 450,
        "currency": "EUR",
        "availability": true,
        "url": "https://booking.com/..."
      },
      {
        "platform": "Hotels.com",
        "price": 480,
        "currency": "EUR",
        "availability": true,
        "url": "https://hotels.com/..."
      }
    ],
    "best_price": {
      "platform": "Booking.com",
      "price": 450,
      "currency": "EUR",
      "url": "https://booking.com/..."
    }
  }
}
```

## Railway Deployment

The `railway.json` is configured with all necessary dependencies:
- Chromium browser and driver
- All required system libraries
- Automatic Playwright setup on build

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Setup Playwright
python setup_playwright.py

# Run with Playwright enabled
ENABLE_PLAYWRIGHT=true uvicorn main:app --reload
```

## Testing

```bash
# Check if Playwright is enabled
curl http://localhost:8000/api/stats

# Test scraping
curl -X POST http://localhost:8000/api/hotels/scrape-prices \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_name": "Hilton Makkah",
    "city": "Makkah",
    "checkin_date": "2024-03-01", 
    "checkout_date": "2024-03-05"
  }'
```

## Error Handling

- Automatic fallback to simulated prices if scraping fails
- All errors tracked in Sentry with context
- Performance monitoring for scraping operations
- Graceful degradation if Playwright initialization fails

## Performance Considerations

- Browser instance is shared across requests (singleton pattern)
- Concurrent scraping from multiple platforms
- 30-second timeout for page loads
- Headless mode for better performance

## Security

- User-Agent rotation to avoid detection
- No personal data is scraped
- Only public pricing information is collected
- All scraped URLs are tracked for compliance