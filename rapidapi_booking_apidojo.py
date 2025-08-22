#!/usr/bin/env python3
"""
🏨 Booking.com API von ApiDojo (Non-Deprecated Version)
Bessere Alternative mit aktiven Endpoints
"""
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class BookingApiDojo:
    """Booking.com API using apidojo endpoints (non-deprecated)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://apidojo-booking-v1.p.rapidapi.com"
        self.headers = {
            'x-rapidapi-host': 'apidojo-booking-v1.p.rapidapi.com',
            'x-rapidapi-key': api_key
        }
        
        # Known destination IDs from Booking.com
        self.known_dest_ids = {
            'makkah': -3096527,
            'mecca': -3096527,
            'medina': -3098025,
            'madinah': -3098025,
            'jeddah': -3097367,
            'riyadh': -3098530
        }
    
    async def auto_complete_location(self, text: str) -> List[Dict]:
        """Search for locations/cities"""
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.base_url}/locations/auto-complete"
                params = {
                    'text': text,
                    'languagecode': 'en-us'
                }
                
                async with session.get(url, headers=self.headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data
                    else:
                        logger.error(f"Location search failed: {resp.status}")
                        return []
                        
            except Exception as e:
                logger.error(f"Error in auto_complete: {e}")
                return []
    
    async def search_hotels(
        self,
        dest_id: int,
        arrival_date: str,
        departure_date: str,
        guest_qty: int = 2,
        room_qty: int = 1,
        children_qty: int = 0,
        children_age: List[int] = None,
        currency_code: str = "EUR",
        price_min: Optional[int] = None,
        price_max: Optional[int] = None,
        categories_filter: Optional[str] = None,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Search hotels using the non-deprecated properties/list endpoint"""
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.base_url}/properties/list"
                
                params = {
                    'offset': offset,
                    'arrival_date': arrival_date,
                    'departure_date': departure_date,
                    'guest_qty': guest_qty,
                    'dest_ids': dest_id,
                    'room_qty': room_qty,
                    'search_type': 'city',
                    'languagecode': 'en-us',
                    'currency_code': currency_code,
                    'order_by': 'popularity'
                }
                
                # Add optional parameters
                if children_qty > 0:
                    params['children_qty'] = children_qty
                    if children_age:
                        params['children_age'] = ','.join(map(str, children_age))
                
                if price_min:
                    params['price_filter_min'] = price_min
                    
                if price_max:
                    params['price_filter_max'] = price_max
                
                if categories_filter:
                    params['categories_filter'] = categories_filter
                
                logger.info(f"🔍 Searching hotels with params: {params}")
                
                async with session.get(url, headers=self.headers, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        error_text = await resp.text()
                        logger.error(f"Hotel search failed: {resp.status} - {error_text}")
                        return {'error': f'API returned {resp.status}'}
                        
            except Exception as e:
                logger.error(f"Error searching hotels: {e}")
                return {'error': str(e)}
    
    async def search_hotels_by_name(
        self,
        hotel_name: str,
        city: str,
        checkin: str,
        checkout: str,
        adults: int = 2,
        rooms: int = 1,
        children: int = 0,
        currency: str = "EUR"
    ) -> Dict[str, Any]:
        """Search hotels by name and city"""
        
        # Check if we know the destination ID
        city_lower = city.lower()
        dest_id = self.known_dest_ids.get(city_lower)
        
        # If not, search for it
        if not dest_id:
            logger.info(f"Searching for destination ID for {city}")
            locations = await self.auto_complete_location(city)
            
            # Find city in results
            for loc in locations:
                if loc.get('city_name', '').lower() == city_lower:
                    dest_id = loc.get('dest_id')
                    break
            
            if not dest_id and locations:
                # Use first result
                dest_id = locations[0].get('dest_id')
        
        if not dest_id:
            return {
                'status': 'error',
                'message': f'Could not find destination ID for {city}'
            }
        
        logger.info(f"Using dest_id {dest_id} for {city}")
        
        # Search hotels
        result = await self.search_hotels(
            dest_id=dest_id,
            arrival_date=checkin,
            departure_date=checkout,
            guest_qty=adults,
            room_qty=rooms,
            children_qty=children,
            currency_code=currency
        )
        
        if 'error' in result:
            return {
                'status': 'error',
                'message': result['error']
            }
        
        # Process results
        hotels = result.get('result', [])
        
        # Find matching hotels
        matching_hotels = []
        hotel_name_lower = hotel_name.lower()
        
        for hotel in hotels:
            name = hotel.get('hotel_name', '').lower()
            
            # Check if hotel name matches
            if hotel_name_lower in name or name in hotel_name_lower:
                matching_hotels.append(hotel)
            elif len(hotel_name_lower.split()) > 1:
                # Check partial matches
                if any(word in name for word in hotel_name_lower.split() if len(word) > 3):
                    matching_hotels.append(hotel)
        
        # Format results
        formatted_results = []
        for hotel in (matching_hotels[:5] if matching_hotels else hotels[:5]):
            # Extract price information
            price_breakdown = hotel.get('composite_price_breakdown', {})
            gross_amount = price_breakdown.get('gross_amount_per_night', {})
            
            formatted_results.append({
                'hotel_name': hotel.get('hotel_name'),
                'hotel_id': hotel.get('hotel_id'),
                'price_per_night': gross_amount.get('value', 0),
                'currency': gross_amount.get('currency', currency),
                'total_price': price_breakdown.get('all_inclusive_amount', {}).get('value', 0),
                'review_score': hotel.get('review_score', 0),
                'review_count': hotel.get('review_nr', 0),
                'review_score_word': hotel.get('review_score_word', ''),
                'photo_url': hotel.get('main_photo_url', ''),
                'distance_to_center': hotel.get('distance_to_cc', 'N/A'),
                'address': hotel.get('address', ''),
                'city': hotel.get('city', ''),
                'available': hotel.get('available_rooms', 0) > 0,
                'class': hotel.get('class', 0),
                'is_free_cancellable': hotel.get('is_free_cancellable', False),
                'exact_match': hotel.get('hotel_name', '').lower() == hotel_name_lower,
                'url': f"https://www.booking.com/hotel/sa/{hotel.get('hotel_name', '').lower().replace(' ', '-')}.html"
            })
        
        # Sort by exact match first, then by price
        formatted_results.sort(key=lambda x: (not x['exact_match'], x['price_per_night']))
        
        # Calculate nights
        checkin_date = datetime.fromisoformat(checkin)
        checkout_date = datetime.fromisoformat(checkout)
        nights = (checkout_date - checkin_date).days
        
        return {
            'status': 'success',
            'hotel_name': hotel_name,
            'city': city,
            'dest_id': dest_id,
            'checkin': checkin,
            'checkout': checkout,
            'nights': nights,
            'adults': adults,
            'rooms': rooms,
            'children': children,
            'currency': currency,
            'total_hotels_found': len(hotels),
            'matching_hotels_found': len(matching_hotels),
            'results': formatted_results,
            'best_price': formatted_results[0] if formatted_results else None,
            'scraped_at': datetime.now().isoformat()
        }


# Test function
async def test_apidojo_api():
    """Test the ApiDojo Booking.com API"""
    
    api = BookingApiDojo('05f220e835mshcb428f0416e1b90p148a1ajsn1a4eec316e79')
    
    print("🧪 Testing ApiDojo Booking.com API...")
    print("=" * 50)
    
    result = await api.search_hotels_by_name(
        hotel_name="Swissôtel Al Maqam Makkah",
        city="Makkah",
        checkin="2025-09-15",
        checkout="2025-09-20",
        adults=2,
        rooms=1,
        currency="EUR"
    )
    
    print(f"\nStatus: {result['status']}")
    
    if result['status'] == 'success':
        print(f"Destination ID: {result.get('dest_id')}")
        print(f"Total hotels found: {result.get('total_hotels_found')}")
        print(f"Matching hotels: {result.get('matching_hotels_found')}")
        print(f"Nights: {result.get('nights')}")
        
        if result.get('best_price'):
            best = result['best_price']
            print(f"\n🏆 Best Match:")
            print(f"  Hotel: {best['hotel_name']}")
            print(f"  Price/night: {best['price_per_night']} {best['currency']}")
            print(f"  Total: {best['total_price']} {best['currency']}")
            print(f"  Rating: {best['review_score']}/10 ({best['review_count']} reviews)")
            print(f"  Distance: {best['distance_to_center']} km from center")
            print(f"  Free cancellation: {best['is_free_cancellable']}")
        
        print(f"\n📋 All Results:")
        for i, hotel in enumerate(result.get('results', []), 1):
            print(f"\n{i}. {hotel['hotel_name']}")
            print(f"   {hotel['price_per_night']} {hotel['currency']}/night")
            print(f"   Rating: {hotel['review_score']}/10")
            print(f"   Distance: {hotel['distance_to_center']} km")
    else:
        print(f"Error: {result.get('message')}")

if __name__ == "__main__":
    asyncio.run(test_apidojo_api())