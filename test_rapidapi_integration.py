#!/usr/bin/env python3
"""
Test script for RapidAPI integration
"""
import asyncio
import json
from rapidapi_booking_apidojo import BookingApiDojo

async def test_rapidapi_integration():
    """Test the RapidAPI integration with real API calls"""
    
    print("🧪 Testing RapidAPI Integration...")
    print("=" * 50)
    
    # Initialize API with provided key
    api_key = "05f220e835mshcb428f0416e1b90p148a1ajsn1a4eec316e79"
    api = BookingApiDojo(api_key)
    
    # Test 1: Search for Swissôtel Al Maqam Makkah
    print("\n📍 Test 1: Swissôtel Al Maqam Makkah")
    print("-" * 30)
    
    result1 = await api.search_hotels_by_name(
        hotel_name="Swissôtel Al Maqam Makkah",
        city="Makkah",
        checkin="2025-09-15",
        checkout="2025-09-20",
        adults=2,
        rooms=1,
        currency="EUR"
    )
    
    print(f"Status: {result1.get('status')}")
    if result1.get('status') == 'success':
        print(f"Hotels found: {result1.get('total_hotels_found')}")
        print(f"Matching hotels: {result1.get('matching_hotels_found')}")
        if result1.get('best_price'):
            best = result1['best_price']
            print(f"Best price: {best['price_per_night']} {best['currency']}/night")
            print(f"Total: {best['total_price']} {best['currency']}")
            print(f"Rating: {best['review_score']}/10")
            print(f"Exact match: {best['exact_match']}")
    else:
        print(f"Error: {result1.get('message')}")
    
    # Test 2: Search for Conrad Makkah
    print("\n📍 Test 2: Conrad Makkah")
    print("-" * 30)
    
    result2 = await api.search_hotels_by_name(
        hotel_name="Conrad Makkah",
        city="Makkah", 
        checkin="2025-09-15",
        checkout="2025-09-20",
        adults=2,
        rooms=1,
        currency="EUR"
    )
    
    print(f"Status: {result2.get('status')}")
    if result2.get('status') == 'success':
        print(f"Hotels found: {result2.get('total_hotels_found')}")
        print(f"Matching hotels: {result2.get('matching_hotels_found')}")
        if result2.get('best_price'):
            best = result2['best_price']
            print(f"Best price: {best['price_per_night']} {best['currency']}/night")
            print(f"Total: {best['total_price']} {best['currency']}")
            print(f"Rating: {best['review_score']}/10")
            print(f"Exact match: {best['exact_match']}")
    else:
        print(f"Error: {result2.get('message')}")
    
    # Test 3: Search in Medina
    print("\n📍 Test 3: Hotel in Medina")
    print("-" * 30)
    
    result3 = await api.search_hotels_by_name(
        hotel_name="Anwar Al Madinah Movenpick Hotel",
        city="Medina",
        checkin="2025-09-15",
        checkout="2025-09-20", 
        adults=2,
        rooms=1,
        currency="EUR"
    )
    
    print(f"Status: {result3.get('status')}")
    if result3.get('status') == 'success':
        print(f"Hotels found: {result3.get('total_hotels_found')}")
        print(f"Matching hotels: {result3.get('matching_hotels_found')}")
        if result3.get('best_price'):
            best = result3['best_price']
            print(f"Best price: {best['price_per_night']} {best['currency']}/night")
            print(f"Total: {best['total_price']} {best['currency']}")
            print(f"Rating: {best['review_score']}/10")
            print(f"Exact match: {best['exact_match']}")
    else:
        print(f"Error: {result3.get('message')}")
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    
    success_count = sum(1 for r in [result1, result2, result3] if r.get('status') == 'success')
    print(f"✅ Successful tests: {success_count}/3")
    print(f"❌ Failed tests: {3-success_count}/3")
    
    if success_count >= 2:
        print("🎉 RapidAPI integration is working!")
        print("✅ Ready for production deployment")
    else:
        print("⚠️ Some tests failed - check API key and endpoints")
    
    print(f"\n🔑 API Key used: {api_key[:10]}...{api_key[-10:]}")
    print(f"🌐 Base URL: https://apidojo-booking-v1.p.rapidapi.com")

if __name__ == "__main__":
    asyncio.run(test_rapidapi_integration())