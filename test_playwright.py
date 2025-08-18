#!/usr/bin/env python3
"""
🧪 Test script for Playwright hotel price scraping
"""
import asyncio
import json
from datetime import datetime, timedelta
from playwright_scraper import scrape_hotel_prices_with_customer_dates

async def test_hotel_scraping():
    """Test scraping with customer dates"""
    
    # Test dates (next month)
    checkin = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    checkout = (datetime.now() + timedelta(days=35)).strftime("%Y-%m-%d")
    
    test_cases = [
        {
            "hotel_name": "Swissôtel Al Maqam Makkah",
            "city": "Makkah",
            "checkin": checkin,
            "checkout": checkout,
            "adults": 2,
            "rooms": 1,
            "children": 0,
            "currency": "EUR"
        },
        {
            "hotel_name": "Conrad Makkah",
            "city": "Makkah", 
            "checkin": checkin,
            "checkout": checkout,
            "adults": 4,
            "rooms": 2,
            "children": 1,
            "currency": "EUR"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test['hotel_name']}")
        print(f"   📅 {test['checkin']} → {test['checkout']}")
        print(f"   👥 {test['adults']} adults, {test['rooms']} rooms, {test['children']} children")
        
        try:
            result = await scrape_hotel_prices_with_customer_dates(**test)
            
            print(f"   ✅ Success!")
            print(f"   🏨 Hotel: {result['hotel_name']}")
            print(f"   🌃 Nights: {result['nights']}")
            
            if result.get('best_price'):
                bp = result['best_price']
                print(f"   💰 Best price: {bp['price_per_night']:.2f} {bp['currency']}/night")
                print(f"   📊 Total: {bp['total_price']:.2f} {bp['currency']} ({bp['platform']})")
            
            print(f"   🔗 Found {len(result['results'])} price sources")
            for r in result['results']:
                status = "✅" if r['availability'] else "❌"
                print(f"      {status} {r['platform']}: {r['price_per_night']:.2f} {r['currency']}/night")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    print("🎭 Testing Playwright Hotel Price Scraping")
    print("=" * 50)
    asyncio.run(test_hotel_scraping())
    print("\n✅ Test completed!")