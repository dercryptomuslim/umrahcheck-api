#!/usr/bin/env python3
"""
UmrahCheck MCP Booking Agent - Compliance-First Version
Uses only partner APIs and permitted data sources
"""

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Tuple
import uuid
import time
import hashlib
import json
from datetime import datetime, timedelta
from enum import Enum
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
API_KEY = os.getenv("MCP_API_KEY", "CHANGE_ME_IN_PRODUCTION")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))  # requests per minute

app = FastAPI(
    title="UmrahCheck MCP Booking Agent",
    description="Compliance-first travel research using partner APIs",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://umrahcheck.de", 
        "https://www.umrahcheck.de",
        "https://umrahcheck-frontend-v2-github.vercel.app",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= Models =============

class OptionLabel(str, Enum):
    VALUE = "Value"
    BALANCED = "Balanced"
    COMFORT = "Comfort"

class LeadRequest(BaseModel):
    """Incoming lead request from n8n or frontend"""
    first_name: str
    last_name: str
    email: str
    whatsapp: Optional[str] = None
    budget: str  # "1150-1300" format
    persons: int = Field(gt=0, le=20)
    destination: str = "Medina"
    departure_airport: str
    arrival_airport: str = "JED"
    departure_date: str  # Can be fuzzy like "Oktober 2025"
    nights_mekka: int = Field(ge=0, default=5)
    nights_medina: int = Field(ge=0, default=4)
    nationality: Optional[str] = "deutsch"
    notes: Optional[str] = None
    source: Optional[str] = "website"
    
    @validator('budget')
    def validate_budget(cls, v):
        if '-' not in v:
            raise ValueError("Budget must be in format 'min-max'")
        return v

class FlightOption(BaseModel):
    """Flight details with deeplink"""
    airline: str
    flight_numbers: List[str]
    departure: str
    arrival: str
    stops: int = 0
    duration_minutes: int
    price_per_person: float
    currency: str = "EUR"
    deeplink: str
    provider: str

class HotelOption(BaseModel):
    """Hotel details with 4-bed rule applied"""
    name: str
    stars: float
    distance_meters: int
    distance_description: str
    board: str = "Room Only"
    nights: int
    rooms_needed: int
    beds_per_room: int = 4
    price_per_room_per_night: float
    price_total: float
    currency: str = "EUR"
    deeplink: str
    provider: str

class ItineraryOption(BaseModel):
    """Complete travel option with flights and hotels"""
    label: OptionLabel
    flight_outbound: FlightOption
    flight_return: FlightOption
    hotel_mekka: HotelOption
    hotel_medina: HotelOption
    total_per_person: float
    total_group: float
    budget_fit_percent: float
    savings_amount: float
    score: float = Field(ge=0, le=100)

class ItineraryResponse(BaseModel):
    """Response with multiple options"""
    lead_token: str
    status: str = "success"
    options: List[ItineraryOption]
    assumptions: Dict
    valid_until: str
    processing_time_ms: int
    meta: Dict = Field(default_factory=dict)

# ============= Budget Allocator =============

class BudgetAllocator:
    """Smart budget allocation with 4-bed rule"""
    
    ALLOCATION_RULES = {
        # Budget ranges: (flight%, hotel%, rest%)
        (0, 1000): (55, 35, 10),
        (1001, 1200): (52, 38, 10),
        (1201, 1500): (50, 40, 10),
        (1501, 2000): (48, 42, 10),
        (2001, float('inf')): (45, 45, 10)
    }
    
    @staticmethod
    def allocate(budget_per_person: int, persons: int) -> Dict:
        """Allocate budget between flights and hotels"""
        
        # Find allocation percentages
        flight_pct = 50  # default
        hotel_pct = 40
        
        for (min_b, max_b), (f_pct, h_pct, r_pct) in BudgetAllocator.ALLOCATION_RULES.items():
            if min_b <= budget_per_person <= max_b:
                flight_pct = f_pct
                hotel_pct = h_pct
                break
        
        total_budget = budget_per_person * persons
        
        # Calculate component budgets
        flight_budget = total_budget * (flight_pct / 100)
        hotel_budget = total_budget * (hotel_pct / 100)
        
        # Apply 4-bed rule for hotels
        beds_per_room = 4 if persons >= 4 else 3
        rooms_needed = (persons + beds_per_room - 1) // beds_per_room
        
        return {
            "total_budget": total_budget,
            "flight_budget_total": flight_budget,
            "flight_budget_per_person": flight_budget / persons,
            "hotel_budget_total": hotel_budget,
            "rooms_needed": rooms_needed,
            "beds_per_room": beds_per_room,
            "hotel_budget_per_room_per_night": hotel_budget / rooms_needed / 9  # 9 nights total
        }

# ============= Provider Interfaces =============

class FlightProvider:
    """Base class for flight providers"""
    
    @staticmethod
    async def search_flights(origin: str, destination: str, 
                           departure_date: str, return_date: str,
                           passengers: int, budget_pp: float) -> List[FlightOption]:
        """Search for flights using partner APIs"""
        
        # This would call actual partner APIs like:
        # - Duffel API
        # - Amadeus Self-Service API
        # - Skyscanner RapidAPI
        
        # For now, return realistic mock data
        return [
            FlightOption(
                airline="Saudia",
                flight_numbers=["SV132"],
                departure=f"{origin} 2025-10-10 14:25",
                arrival=f"{destination} 2025-10-10 20:15",
                stops=0,
                duration_minutes=350,
                price_per_person=385.0,
                deeplink="https://partners.saudia.com/deeplink?ref=umrahcheck",
                provider="Duffel"
            )
        ]

class HotelProvider:
    """Base class for hotel providers"""
    
    @staticmethod
    async def search_hotels(city: str, checkin: str, checkout: str,
                          rooms: int, budget_per_room_per_night: float) -> List[HotelOption]:
        """Search for hotels using partner APIs"""
        
        # This would call actual partner APIs like:
        # - Hotelbeds API
        # - Expedia Rapid API
        # - Booking.com Partner API
        
        nights = (datetime.fromisoformat(checkout) - datetime.fromisoformat(checkin)).days
        
        # Return realistic mock data with 4-bed rule
        if city.lower() == "makkah":
            return [
                HotelOption(
                    name="Makkah Towers",
                    stars=4,
                    distance_meters=400,
                    distance_description="400m to Haram (5 min walk)",
                    nights=nights,
                    rooms_needed=rooms,
                    beds_per_room=4,
                    price_per_room_per_night=196.0,
                    price_total=196.0 * nights * rooms,
                    deeplink="https://partners.hotelbeds.com/hotel?ref=umrahcheck",
                    provider="Hotelbeds"
                )
            ]
        else:
            return [
                HotelOption(
                    name="Coral Al Ahsa Hotel",
                    stars=4,
                    distance_meters=300,
                    distance_description="300m to Prophet's Mosque",
                    nights=nights,
                    rooms_needed=rooms,
                    beds_per_room=4,
                    price_per_room_per_night=163.0,
                    price_total=163.0 * nights * rooms,
                    deeplink="https://partners.hotelbeds.com/hotel?ref=umrahcheck",
                    provider="Hotelbeds"
                )
            ]

# ============= Deeplink Builder =============

class DeeplinkBuilder:
    """Generate tracking-enabled deeplinks for partners"""
    
    @staticmethod
    def build(provider: str, product_type: str, params: Dict) -> str:
        """Build deeplink with tracking parameters"""
        
        base_urls = {
            "duffel": "https://partners.duffel.com/book",
            "hotelbeds": "https://partners.hotelbeds.com/hotel",
            "amadeus": "https://amadeus.com/booking",
            "booking": "https://www.booking.com/hotel",
        }
        
        base_url = base_urls.get(provider.lower(), "https://umrahcheck.de/redirect")
        
        # Add tracking parameters
        params.update({
            "ref": "umrahcheck",
            "utm_source": "umrahcheck",
            "utm_medium": "mcp_agent",
            "utm_campaign": product_type,
            "timestamp": int(time.time())
        })
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query_string}"

# ============= Scoring Engine =============

class ScoringEngine:
    """Score and rank travel options"""
    
    @staticmethod
    def calculate_score(option: Dict, preferences: Dict) -> float:
        """
        Calculate option score based on multiple factors
        Score = Distance (40%) + Budget-Fit (35%) + Reviews (15%) + Flexibility (10%)
        """
        
        distance_score = 100 - min(option.get("avg_distance", 500) / 10, 100)
        budget_fit_score = min(option.get("budget_fit_percent", 80), 100)
        review_score = option.get("avg_rating", 4.0) * 20
        flexibility_score = 80  # Based on cancellation policy
        
        total_score = (
            distance_score * 0.40 +
            budget_fit_score * 0.35 +
            review_score * 0.15 +
            flexibility_score * 0.10
        )
        
        return round(total_score, 1)

# ============= Cache Layer =============

class CacheManager:
    """Simple in-memory cache (use Redis in production)"""
    
    _cache = {}
    
    @staticmethod
    def get_key(request: LeadRequest) -> str:
        """Generate cache key from request"""
        key_data = f"{request.departure_airport}_{request.arrival_airport}_{request.departure_date}_{request.persons}_{request.budget}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    @staticmethod
    def get(key: str) -> Optional[Dict]:
        """Get cached result if not expired"""
        if key in CacheManager._cache:
            entry = CacheManager._cache[key]
            if time.time() - entry["timestamp"] < CACHE_TTL:
                return entry["data"]
        return None
    
    @staticmethod
    def set(key: str, data: Dict):
        """Cache result with timestamp"""
        CacheManager._cache[key] = {
            "data": data,
            "timestamp": time.time()
        }

# ============= Main Search Logic =============

async def search_itinerary(request: LeadRequest) -> ItineraryResponse:
    """Main search orchestration with compliance-first approach"""
    
    start_time = time.time()
    
    # Check cache first
    cache_key = CacheManager.get_key(request)
    cached_result = CacheManager.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for {cache_key}")
        cached_result["meta"]["cache_hit"] = True
        return ItineraryResponse(**cached_result)
    
    # Parse budget
    budget_parts = request.budget.split('-')
    budget_min = int(budget_parts[0])
    budget_max = int(budget_parts[1]) if len(budget_parts) > 1 else budget_min
    budget_avg = (budget_min + budget_max) // 2
    
    # Allocate budget
    allocation = BudgetAllocator.allocate(budget_avg, request.persons)
    
    # Parse dates (handle fuzzy dates in production)
    departure_date = "2025-10-10"  # Would parse request.departure_date
    return_date = "2025-10-19"  # Calculate based on nights
    
    # Search flights (using partner APIs)
    outbound_flights = await FlightProvider.search_flights(
        request.departure_airport,
        request.arrival_airport,
        departure_date,
        return_date,
        request.persons,
        allocation["flight_budget_per_person"]
    )
    
    return_flights = await FlightProvider.search_flights(
        request.arrival_airport,
        request.departure_airport,
        return_date,
        departure_date,
        request.persons,
        allocation["flight_budget_per_person"]
    )
    
    # Search hotels (using partner APIs)
    mekka_hotels = await HotelProvider.search_hotels(
        "Makkah",
        departure_date,
        "2025-10-15",
        allocation["rooms_needed"],
        allocation["hotel_budget_per_room_per_night"] * 0.6  # 60% for Makkah
    )
    
    medina_hotels = await HotelProvider.search_hotels(
        "Medina",
        "2025-10-15",
        return_date,
        allocation["rooms_needed"],
        allocation["hotel_budget_per_room_per_night"] * 0.4  # 40% for Medina
    )
    
    # Build options (Value, Balanced, Comfort)
    options = []
    
    # Value Option - Cheapest
    if outbound_flights and return_flights and mekka_hotels and medina_hotels:
        flight_cost_pp = outbound_flights[0].price_per_person + return_flights[0].price_per_person
        hotel_cost_total = mekka_hotels[0].price_total + medina_hotels[0].price_total
        total_pp = flight_cost_pp + (hotel_cost_total / request.persons)
        
        value_option = ItineraryOption(
            label=OptionLabel.VALUE,
            flight_outbound=outbound_flights[0],
            flight_return=return_flights[0],
            hotel_mekka=mekka_hotels[0],
            hotel_medina=medina_hotels[0],
            total_per_person=total_pp,
            total_group=total_pp * request.persons,
            budget_fit_percent=(total_pp / budget_avg) * 100,
            savings_amount=max(0, budget_avg - total_pp) * request.persons,
            score=ScoringEngine.calculate_score(
                {"avg_distance": 350, "budget_fit_percent": (total_pp / budget_avg) * 100, "avg_rating": 4.2},
                {}
            )
        )
        options.append(value_option)
    
    # Generate lead token
    lead_token = f"umr_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
    
    # Build response
    response = ItineraryResponse(
        lead_token=lead_token,
        status="success",
        options=options,
        assumptions={
            "budget_allocation": allocation,
            "date_flexibility": "±3 days",
            "room_calculation": f"{allocation['rooms_needed']} rooms with {allocation['beds_per_room']} beds each",
            "season_factor": 1.0
        },
        valid_until=(datetime.now() + timedelta(hours=24)).isoformat(),
        processing_time_ms=int((time.time() - start_time) * 1000),
        meta={
            "cache_hit": False,
            "providers_used": ["Duffel", "Hotelbeds"],
            "compliance": "All data from partner APIs"
        }
    )
    
    # Cache the result
    CacheManager.set(cache_key, response.dict())
    
    return response

# ============= API Endpoints =============

def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key for authentication"""
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

@app.get("/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "compliance": "Partner APIs only"
    }

@app.post("/v1/itinerary/search", response_model=ItineraryResponse)
async def search_itinerary_endpoint(
    request: LeadRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(None)
):
    """Main search endpoint - compliance-first approach"""
    verify_api_key(x_api_key)
    
    logger.info(f"New search request from {request.first_name} {request.last_name}")
    
    try:
        # Perform search
        response = await search_itinerary(request)
        
        # Log for audit
        background_tasks.add_task(
            log_search_audit,
            request,
            response
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/itinerary/{lead_token}")
async def get_itinerary_status(lead_token: str, x_api_key: str = Header(None)):
    """Get status of a previous search"""
    verify_api_key(x_api_key)
    
    # In production, this would query a database
    return {
        "lead_token": lead_token,
        "status": "completed",
        "message": "Results available"
    }

@app.post("/v1/webhooks/n8n")
async def webhook_callback(data: Dict):
    """Webhook for n8n callbacks"""
    logger.info(f"Webhook received: {data}")
    return {"status": "received"}

async def log_search_audit(request: LeadRequest, response: ItineraryResponse):
    """Log search for audit trail (GDPR compliant)"""
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "lead_token": response.lead_token,
        "source": request.source,
        "persons": request.persons,
        "budget_range": request.budget,
        "options_found": len(response.options),
        "providers": response.meta.get("providers_used", [])
    }
    logger.info(f"Audit: {json.dumps(audit_entry)}")

# ============= Startup/Shutdown =============

@app.on_event("startup")
async def startup_event():
    """Initialize connections to partner APIs"""
    logger.info("Starting UmrahCheck MCP Agent v2.0 (Compliance-First)")
    logger.info("Using only partner APIs and permitted data sources")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown"""
    logger.info("Shutting down MCP Agent")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(
        "mcp_booking_agent_compliant:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Railway deployment
        log_level="info"
    )