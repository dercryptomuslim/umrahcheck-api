"""
Mock Provider Implementation für MCP Agent
Verwendet realistische Daten ohne externe Partner APIs
Kann später einfach durch echte APIs ersetzt werden
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict
import logging

from mcp_agent import FlightOption, HotelOption

logger = logging.getLogger(__name__)

class MockFlightProvider:
    """Mock flight provider mit realistischen Daten"""
    
    AIRLINES = [
        {"name": "Saudia", "quality": "high", "price_factor": 1.0},
        {"name": "Emirates", "quality": "premium", "price_factor": 1.3},
        {"name": "Turkish Airlines", "quality": "good", "price_factor": 0.9},
        {"name": "Lufthansa", "quality": "high", "price_factor": 1.1},
        {"name": "Qatar Airways", "quality": "premium", "price_factor": 1.2},
        {"name": "Egyptair", "quality": "economy", "price_factor": 0.8}
    ]
    
    @staticmethod
    async def search_flights(origin: str, destination: str, 
                           departure_date: str, return_date: str,
                           passengers: int, budget_pp: float) -> List[FlightOption]:
        """Search for flights using realistic mock data"""
        
        logger.info(f"🛫 Mock flight search: {origin} → {destination}, Budget: €{budget_pp}")
        
        # Simulate API delay
        await asyncio.sleep(0.2)
        
        flights = []
        
        # Generate 2-3 flight options
        for i, airline in enumerate(MockFlightProvider.AIRLINES[:3]):
            base_price = 350  # Base price EUR
            
            # Price variation based on airline and budget
            price_factor = airline["price_factor"]
            if budget_pp < 600:  # Low budget
                price_factor *= 0.8
            elif budget_pp > 800:  # High budget  
                price_factor *= 1.2
                
            final_price = base_price * price_factor + random.randint(-50, 50)
            
            # Generate flight number
            airline_codes = {
                "Saudia": "SV", "Emirates": "EK", "Turkish Airlines": "TK",
                "Lufthansa": "LH", "Qatar Airways": "QR", "Egyptair": "MS"
            }
            
            flight_num = f"{airline_codes.get(airline['name'], 'XX')}{random.randint(100, 999)}"
            
            # Calculate duration and stops
            duration = 350 + random.randint(-60, 120)  # 5-7 hours
            stops = 0 if airline["quality"] in ["premium", "high"] else random.randint(0, 1)
            
            flight = FlightOption(
                airline=airline["name"],
                flight_numbers=[flight_num],
                departure=f"{origin} {departure_date} {random.randint(6, 23):02d}:{random.randint(0, 59):02d}",
                arrival=f"{destination} {departure_date} {random.randint(10, 23):02d}:{random.randint(0, 59):02d}",
                stops=stops,
                duration_minutes=duration,
                price_per_person=round(final_price, 2),
                deeplink=f"https://umrahcheck.de/redirect/flights?airline={airline['name']}&price={final_price}&ref=mcp",
                provider="UmrahCheck Mock API"
            )
            
            flights.append(flight)
        
        # Sort by price (Value option first)
        flights.sort(key=lambda x: x.price_per_person)
        
        logger.info(f"✅ Generated {len(flights)} flight options")
        return flights

class MockHotelProvider:
    """Mock hotel provider mit realistischen Makkah/Medina Hotels"""
    
    MAKKAH_HOTELS = [
        {
            "name": "Fairmont Makkah Clock Royal Tower",
            "stars": 5,
            "distance_meters": 100,
            "base_price": 220,
            "quality": "premium"
        },
        {
            "name": "Conrad Makkah",
            "stars": 5,
            "distance_meters": 150,
            "base_price": 200,
            "quality": "high"
        },
        {
            "name": "Pullman ZamZam Makkah",
            "stars": 5,
            "distance_meters": 200,
            "base_price": 180,
            "quality": "high"
        },
        {
            "name": "Makkah Towers",
            "stars": 4,
            "distance_meters": 400,
            "base_price": 130,
            "quality": "good"
        },
        {
            "name": "Al Masa Hotel",
            "stars": 3,
            "distance_meters": 800,
            "base_price": 80,
            "quality": "economy"
        }
    ]
    
    MEDINA_HOTELS = [
        {
            "name": "Anwar Al Madinah Movenpick",
            "stars": 5,
            "distance_meters": 100,
            "base_price": 180,
            "quality": "premium"
        },
        {
            "name": "Shaza Al Madina",
            "stars": 5,
            "distance_meters": 200,
            "base_price": 160,
            "quality": "high"
        },
        {
            "name": "Coral Al Ahsa Hotel",
            "stars": 4,
            "distance_meters": 300,
            "base_price": 120,
            "quality": "good"
        },
        {
            "name": "Al Aqeeq Hotel",
            "stars": 3,
            "distance_meters": 500,
            "base_price": 90,
            "quality": "good"
        },
        {
            "name": "Elaf Al Mashaer",
            "stars": 3,
            "distance_meters": 600,
            "base_price": 70,
            "quality": "economy"
        }
    ]
    
    @staticmethod
    async def search_hotels(city: str, checkin: str, checkout: str,
                          rooms: int, budget_per_room_per_night: float) -> List[HotelOption]:
        """Search for hotels using realistic mock data"""
        
        logger.info(f"🏨 Mock hotel search: {city}, Budget: €{budget_per_room_per_night}/room/night")
        
        # Simulate API delay
        await asyncio.sleep(0.3)
        
        # Select hotel list based on city
        if city.lower() in ["makkah", "mecca"]:
            hotel_list = MockHotelProvider.MAKKAH_HOTELS
            location_name = "Haram"
        else:
            hotel_list = MockHotelProvider.MEDINA_HOTELS
            location_name = "Prophet's Mosque"
        
        nights = (datetime.fromisoformat(checkout) - datetime.fromisoformat(checkin)).days
        hotels = []
        
        # Generate hotel options based on budget
        for hotel_data in hotel_list:
            # Adjust price based on budget and season
            price_factor = 1.0
            
            if budget_per_room_per_night < 100:  # Budget search
                if hotel_data["quality"] in ["premium", "high"]:
                    continue  # Skip expensive hotels
                price_factor = 0.9
            elif budget_per_room_per_night > 200:  # Luxury search
                if hotel_data["quality"] == "economy":
                    continue  # Skip budget hotels
                price_factor = 1.1
            
            # Add seasonal variation
            price_factor += random.uniform(-0.1, 0.1)
            
            final_price = hotel_data["base_price"] * price_factor
            
            # Skip if over budget
            if final_price > budget_per_room_per_night * 1.2:
                continue
            
            # Generate distance description
            distance_desc = f"{hotel_data['distance_meters']}m to {location_name}"
            if hotel_data['distance_meters'] <= 200:
                distance_desc += " (2 min walk)"
            elif hotel_data['distance_meters'] <= 500:
                distance_desc += " (5 min walk)"
            else:
                distance_desc += " (10 min walk)"
            
            hotel = HotelOption(
                name=hotel_data["name"],
                stars=hotel_data["stars"],
                distance_meters=hotel_data["distance_meters"],
                distance_description=distance_desc,
                board="Room Only",
                nights=nights,
                rooms_needed=rooms,
                beds_per_room=4,  # 4-bed rule
                price_per_room_per_night=round(final_price, 2),
                price_total=round(final_price * nights * rooms, 2),
                deeplink=f"https://umrahcheck.de/redirect/hotels?hotel={hotel_data['name']}&price={final_price}&ref=mcp",
                provider="UmrahCheck Mock API"
            )
            
            hotels.append(hotel)
        
        # Sort by value (distance vs price)
        hotels.sort(key=lambda x: (x.distance_meters / 100) + (x.price_per_room_per_night / 50))
        
        # Return top 3 options
        result = hotels[:3]
        logger.info(f"✅ Generated {len(result)} hotel options for {city}")
        
        return result

class MockProviderManager:
    """Manager für alle Mock Provider"""
    
    @staticmethod
    def get_provider_status():
        """Get status of all mock providers"""
        return {
            "flights": {
                "provider": "UmrahCheck Mock API",
                "airlines_available": len(MockFlightProvider.AIRLINES),
                "status": "active"
            },
            "hotels": {
                "provider": "UmrahCheck Mock API", 
                "makkah_hotels": len(MockHotelProvider.MAKKAH_HOTELS),
                "medina_hotels": len(MockHotelProvider.MEDINA_HOTELS),
                "status": "active"
            },
            "partner_apis": {
                "duffel": "not_configured",
                "amadeus": "not_configured", 
                "hotelbeds": "not_configured",
                "note": "Using realistic mock data until partner APIs are available"
            }
        }
    
    @staticmethod
    async def test_all_providers():
        """Test all mock providers"""
        try:
            # Test flight search
            flights = await MockFlightProvider.search_flights(
                "FRA", "JED", "2025-10-10", "2025-10-19", 4, 400
            )
            
            # Test hotel search  
            hotels_makkah = await MockHotelProvider.search_hotels(
                "Makkah", "2025-10-10", "2025-10-15", 1, 150
            )
            
            hotels_medina = await MockHotelProvider.search_hotels(
                "Medina", "2025-10-15", "2025-10-19", 1, 150  
            )
            
            return {
                "test_status": "success",
                "flights_found": len(flights),
                "makkah_hotels_found": len(hotels_makkah),
                "medina_hotels_found": len(hotels_medina),
                "sample_flight_price": flights[0].price_per_person if flights else None,
                "sample_hotel_price": hotels_makkah[0].price_per_room_per_night if hotels_makkah else None
            }
            
        except Exception as e:
            return {
                "test_status": "failed", 
                "error": str(e)
            }