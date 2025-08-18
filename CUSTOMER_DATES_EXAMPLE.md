# 🎭 Customer-Specific Hotel Price Scraping

## Overview

The enhanced Playwright integration now supports customer-specific parameters:
- **Exact check-in/check-out dates** from the customer
- **Number of adults, children, and rooms**
- **Preferred currency** (EUR, USD, SAR)
- **60-second caching** to avoid redundant scraping
- **Rate limiting** per domain (2 concurrent requests)

## API Usage

### Enhanced Request Format

```json
POST /api/hotels/scrape-prices
{
  "hotel_name": "Swissôtel Al Maqam Makkah",
  "city": "Makkah",
  "checkin_date": "2024-03-15",
  "checkout_date": "2024-03-20",
  "adults": 2,
  "rooms": 1,
  "children": 0,
  "currency": "EUR"
}
```

### Enhanced Response Format

```json
{
  "status": "success",
  "data": {
    "hotel_name": "Swissôtel Al Maqam Makkah",
    "city": "Makkah",
    "checkin": "2024-03-15",
    "checkout": "2024-03-20",
    "nights": 5,
    "adults": 2,
    "rooms": 1,
    "children": 0,
    "currency": "EUR",
    "results": [
      {
        "platform": "Booking.com",
        "price_per_night": 450.00,
        "total_price": 2250.00,
        "currency": "EUR",
        "availability": true,
        "url": "https://booking.com/hotel/sa/swissotel-makkah.de.html?checkin=2024-03-15&checkout=2024-03-20&group_adults=2&no_rooms=1",
        "error": null,
        "scraped_at": "2024-01-17T15:30:00"
      }
    ],
    "best_price": {
      "platform": "Booking.com",
      "price_per_night": 450.00,
      "total_price": 2250.00,
      "currency": "EUR",
      "url": "https://booking.com/...",
      "nights": 5
    },
    "scraped_at": "2024-01-17T15:30:00",
    "cache_expires": 1705509060
  }
}
```

## Real Customer Scenarios

### Family with Children
```bash
curl -X POST https://umrahcheck-api-production.up.railway.app/api/hotels/scrape-prices \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_name": "Conrad Makkah",
    "city": "Makkah",
    "checkin_date": "2024-04-01",
    "checkout_date": "2024-04-07",
    "adults": 2,
    "rooms": 1,
    "children": 2,
    "currency": "EUR"
  }'
```

### Group Booking
```bash
curl -X POST https://umrahcheck-api-production.up.railway.app/api/hotels/scrape-prices \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_name": "Hilton Makkah Convention Hotel",
    "city": "Makkah",
    "checkin_date": "2024-05-15",
    "checkout_date": "2024-05-22",
    "adults": 8,
    "rooms": 4,
    "children": 0,
    "currency": "EUR"
  }'
```

### Different Currency
```bash
curl -X POST https://umrahcheck-api-production.up.railway.app/api/hotels/scrape-prices \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_name": "InterContinental Dar Al Tawhid Makkah",
    "city": "Makkah",
    "checkin_date": "2024-06-10",
    "checkout_date": "2024-06-15",
    "adults": 2,
    "rooms": 1,
    "children": 0,
    "currency": "SAR"
  }'
```

## Built URLs Examples

### Booking.com URL Structure
```
https://www.booking.com/hotel/sa/swissotel-makkah.de.html?
  checkin=2024-03-15&
  checkout=2024-03-20&
  group_adults=2&
  group_children=0&
  no_rooms=1&
  selected_currency=EUR&
  lang=de
```

### HalalBooking.com URL Structure
```
https://www.halalbooking.com/hotels/swissotel-al-maqam-makkah?
  checkin=2024-03-15&
  checkout=2024-03-20&
  adults=2&
  children=0&
  rooms=1&
  currency=EUR&
  lang=de
```

## Performance Features

### Caching System
- **60-second TTL** per unique request combination
- **Cache key**: (hotel_name, city, checkin, checkout, adults, rooms, children, currency)
- **Automatic expiry** with timestamp tracking

### Rate Limiting
- **Per-domain semaphores**: Max 2 concurrent requests per platform
- **Prevents anti-bot triggers** from too many simultaneous requests
- **Fair resource sharing** across multiple customers

### Error Handling
- **Graceful fallbacks** if scraping fails
- **Detailed error context** in Sentry
- **Robust selector fallbacks** for DOM changes
- **Cookie handling** for all major platforms

## Frontend Integration

### React Hook Example
```typescript
const useHotelPrices = (searchParams) => {
  const [prices, setPrices] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const fetchPrices = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/hotels/scrape-prices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(searchParams)
      });
      const data = await response.json();
      setPrices(data.data);
    } catch (error) {
      console.error('Price fetch failed:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return { prices, loading, fetchPrices };
};
```

### Usage in Component
```tsx
const HotelBooking = () => {
  const { prices, loading, fetchPrices } = useHotelPrices();
  
  const searchPrices = () => {
    fetchPrices({
      hotel_name: "Swissôtel Al Maqam Makkah",
      city: "Makkah",
      checkin_date: "2024-03-15",
      checkout_date: "2024-03-20",
      adults: 2,
      rooms: 1,
      children: 0,
      currency: "EUR"
    });
  };
  
  return (
    <div>
      <button onClick={searchPrices} disabled={loading}>
        {loading ? 'Searching...' : 'Get Real Prices'}
      </button>
      
      {prices?.best_price && (
        <div className="price-result">
          <h3>Best Price Found</h3>
          <p>{prices.best_price.price_per_night}€ per night</p>
          <p>Total: {prices.best_price.total_price}€ for {prices.nights} nights</p>
          <a href={prices.best_price.url} target="_blank">
            Book on {prices.best_price.platform}
          </a>
        </div>
      )}
    </div>
  );
};
```

## Next Steps

1. **Add more platforms**: Hotels.com, Expedia, HalalBooking.com
2. **Airtable integration**: Load hotel slugs from your database
3. **Price history**: Store prices for trend analysis
4. **Affiliate links**: Add your partner IDs to URLs
5. **Queue system**: Background price updates for popular hotels