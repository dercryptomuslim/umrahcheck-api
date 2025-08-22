"""
MCP Integration mit Mock Providers
Verwendet realistische Mock-Daten anstatt Partner APIs
"""
from fastapi import HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
import logging
from datetime import datetime
import asyncio

# Import Mock Providers statt echter APIs
from mcp_mock_providers import MockFlightProvider, MockHotelProvider, MockProviderManager

# Import MCP Agent components (Models etc.)
from mcp_agent import (
    LeadRequest, 
    ItineraryResponse,
    ItineraryOption,
    OptionLabel,
    BudgetAllocator,
    ScoringEngine,
    CacheManager
)

# Sentry integration
from sentry_config import (
    capture_api_error, 
    set_transaction_context,
    track_airtable_request,
    get_logger
)

logger = get_logger(__name__)

# Extended models für Frontend Integration (same as before)
class FrontendLeadRequest(BaseModel):
    """Extended lead request from frontend forms"""
    first_name: str
    last_name: str
    email: str
    whatsapp: Optional[str] = None
    budget: str  # "1150-1300" format
    persons: int = Field(gt=0, le=20)
    departure_airport: str
    departure_date: str  # Can be fuzzy
    
    # Optional fields with defaults
    destination: str = "Medina"
    arrival_airport: str = "JED"
    nights_mekka: int = Field(ge=0, default=5)
    nights_medina: int = Field(ge=0, default=4)
    nationality: str = "deutsch"
    notes: Optional[str] = None
    source: str = "frontend"
    
    @validator('budget')
    def validate_budget(cls, v):
        if '-' not in v:
            # Single budget value - create range
            budget_val = int(v)
            return f"{budget_val}-{budget_val + 200}"
        return v

class MCPSearchResponse(BaseModel):
    """Response wrapper für Frontend"""
    success: bool
    lead_token: str
    options: List[Dict]
    meta: Dict
    assumptions: Dict
    valid_until: str
    processing_time_ms: int
    message: Optional[str] = None

async def search_itinerary_mock(request: LeadRequest) -> ItineraryResponse:
    """
    Main search orchestration with MOCK providers
    Gleiche Logik wie original, aber mit Mock-Daten
    """
    
    start_time = datetime.now().timestamp() * 1000
    
    logger.info(f"🔍 Starting MOCK search for {request.first_name} {request.last_name}")
    
    # Check cache first (optional für Mock)
    # cache_key = CacheManager.get_key(request)
    # cached_result = CacheManager.get(cache_key)
    
    # Parse budget
    budget_parts = request.budget.split('-')
    budget_min = int(budget_parts[0])
    budget_max = int(budget_parts[1]) if len(budget_parts) > 1 else budget_min
    budget_avg = (budget_min + budget_max) // 2
    
    # Allocate budget (same logic)
    allocation = BudgetAllocator.allocate(budget_avg, request.persons)
    
    logger.info(f"💰 Budget allocation: €{allocation['flight_budget_per_person']}/person flights, €{allocation['hotel_budget_per_room_per_night']}/room/night hotels")
    
    # Parse dates (würde in Production request.departure_date parsen)
    departure_date = "2025-10-10"  
    return_date = "2025-10-19"  
    
    try:
        # Search flights mit Mock Provider
        outbound_flights = await MockFlightProvider.search_flights(
            request.departure_airport,
            request.arrival_airport,
            departure_date,
            return_date,
            request.persons,
            allocation["flight_budget_per_person"]
        )
        
        return_flights = await MockFlightProvider.search_flights(
            request.arrival_airport,
            request.departure_airport,
            return_date,
            departure_date,
            request.persons,
            allocation["flight_budget_per_person"]
        )
        
        # Search hotels mit Mock Provider
        mekka_hotels = await MockHotelProvider.search_hotels(
            "Makkah",
            departure_date,
            "2025-10-15",
            allocation["rooms_needed"],
            allocation["hotel_budget_per_room_per_night"] * 0.6  # 60% for Makkah
        )
        
        medina_hotels = await MockHotelProvider.search_hotels(
            "Medina",
            "2025-10-15", 
            return_date,
            allocation["rooms_needed"],
            allocation["hotel_budget_per_room_per_night"] * 0.4  # 40% for Medina
        )
        
    except Exception as e:
        logger.error(f"❌ Mock provider search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    
    # Build options (Value, Balanced, Comfort)
    options = []
    
    if outbound_flights and return_flights and mekka_hotels and medina_hotels:
        
        # VALUE Option - Cheapest combination
        flight_cost_pp = outbound_flights[0].price_per_person + return_flights[0].price_per_person
        hotel_cost_total = mekka_hotels[-1].price_total + medina_hotels[-1].price_total  # Cheapest hotels
        total_pp = flight_cost_pp + (hotel_cost_total / request.persons)
        
        value_option = ItineraryOption(
            label=OptionLabel.VALUE,
            flight_outbound=outbound_flights[0],
            flight_return=return_flights[0],
            hotel_mekka=mekka_hotels[-1] if len(mekka_hotels) > 1 else mekka_hotels[0],
            hotel_medina=medina_hotels[-1] if len(medina_hotels) > 1 else medina_hotels[0],
            total_per_person=round(total_pp, 2),
            total_group=round(total_pp * request.persons, 2),
            budget_fit_percent=min(round((total_pp / budget_avg) * 100, 1), 100),
            savings_amount=max(0, round((budget_avg - total_pp) * request.persons, 2)),
            score=ScoringEngine.calculate_score(
                {"avg_distance": 500, "budget_fit_percent": (total_pp / budget_avg) * 100, "avg_rating": 3.8},
                {}
            )
        )
        options.append(value_option)
        
        # BALANCED Option - Best value hotels
        if len(mekka_hotels) > 1 and len(medina_hotels) > 1:
            hotel_cost_total = mekka_hotels[0].price_total + medina_hotels[0].price_total
            total_pp = flight_cost_pp + (hotel_cost_total / request.persons)
            
            balanced_option = ItineraryOption(
                label=OptionLabel.BALANCED,
                flight_outbound=outbound_flights[1] if len(outbound_flights) > 1 else outbound_flights[0],
                flight_return=return_flights[1] if len(return_flights) > 1 else return_flights[0],
                hotel_mekka=mekka_hotels[0],
                hotel_medina=medina_hotels[0],
                total_per_person=round(total_pp, 2),
                total_group=round(total_pp * request.persons, 2),
                budget_fit_percent=min(round((total_pp / budget_avg) * 100, 1), 100),
                savings_amount=max(0, round((budget_avg - total_pp) * request.persons, 2)),
                score=ScoringEngine.calculate_score(
                    {"avg_distance": 250, "budget_fit_percent": (total_pp / budget_avg) * 100, "avg_rating": 4.3},
                    {}
                )
            )
            options.append(balanced_option)
        
        # COMFORT Option - Premium wenn Budget erlaubt
        if budget_avg > 1200 and len(outbound_flights) > 2:
            hotel_cost_total = mekka_hotels[0].price_total + medina_hotels[0].price_total
            flight_cost_pp = outbound_flights[-1].price_per_person + return_flights[-1].price_per_person  # Premium flights
            total_pp = flight_cost_pp + (hotel_cost_total / request.persons)
            
            if total_pp <= budget_max * 1.1:  # Allow 10% over budget for comfort
                comfort_option = ItineraryOption(
                    label=OptionLabel.COMFORT,
                    flight_outbound=outbound_flights[-1],
                    flight_return=return_flights[-1],
                    hotel_mekka=mekka_hotels[0],
                    hotel_medina=medina_hotels[0],
                    total_per_person=round(total_pp, 2),
                    total_group=round(total_pp * request.persons, 2),
                    budget_fit_percent=min(round((total_pp / budget_avg) * 100, 1), 100),
                    savings_amount=max(0, round((budget_avg - total_pp) * request.persons, 2)),
                    score=ScoringEngine.calculate_score(
                        {"avg_distance": 150, "budget_fit_percent": (total_pp / budget_avg) * 100, "avg_rating": 4.7},
                        {}
                    )
                )
                options.append(comfort_option)
    
    # Generate lead token
    lead_token = f"umr_mock_{datetime.now().strftime('%Y%m%d')}_{request.first_name[:2]}{request.persons}"
    
    # Calculate processing time
    end_time = datetime.now().timestamp() * 1000
    processing_time = int(end_time - start_time)
    
    # Build response
    response = ItineraryResponse(
        lead_token=lead_token,
        status="success",
        options=options,
        assumptions={
            "budget_allocation": allocation,
            "date_flexibility": "±3 days",
            "room_calculation": f"{allocation['rooms_needed']} rooms with {allocation['beds_per_room']} beds each",
            "season_factor": 1.0,
            "provider_type": "mock_data",
            "note": "Using realistic mock data - will be replaced with partner APIs"
        },
        valid_until=(datetime.now() + timedelta(hours=24)).isoformat(),
        processing_time_ms=processing_time,
        meta={
            "cache_hit": False,
            "providers_used": ["UmrahCheck Mock API"],
            "compliance": "Mock data - no external API calls",
            "flights_found": len(outbound_flights),
            "hotels_found": f"{len(mekka_hotels)} Makkah, {len(medina_hotels)} Medina",
            "mock_mode": True
        }
    )
    
    logger.info(f"✅ Mock search completed: {len(options)} options, {processing_time}ms")
    
    return response

async def mcp_compliance_search_mock(
    request: FrontendLeadRequest,
    background_tasks: BackgroundTasks
) -> MCPSearchResponse:
    """
    MCP search mit Mock providers - gleiche Interface wie echte Version
    """
    try:
        # Add Sentry tracking
        set_transaction_context("mcp_mock_search", {
            "customer": f"{request.first_name} {request.last_name}",
            "budget": request.budget,
            "persons": request.persons,
            "departure": request.departure_airport,
            "source": request.source
        })
        
        logger.info(f"🔍 MCP MOCK search started for {request.first_name} {request.last_name}")
        
        # Convert frontend request to MCP format
        mcp_request = LeadRequest(
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email,
            whatsapp=request.whatsapp,
            budget=request.budget,
            persons=request.persons,
            destination=request.destination,
            departure_airport=request.departure_airport,
            arrival_airport=request.arrival_airport,
            departure_date=request.departure_date,
            nights_mekka=request.nights_mekka,
            nights_medina=request.nights_medina,
            nationality=request.nationality,
            notes=request.notes,
            source=request.source
        )
        
        # Perform MCP search mit Mock providers
        mcp_result = await search_itinerary_mock(mcp_request)
        
        # Convert options für Frontend-friendly format (same as original)
        frontend_options = []
        for option in mcp_result.options:
            frontend_option = {
                "label": option.label,
                "flights": {
                    "outbound": {
                        "airline": option.flight_outbound.airline,
                        "price_per_person": option.flight_outbound.price_per_person,
                        "departure": option.flight_outbound.departure,
                        "arrival": option.flight_outbound.arrival,
                        "duration_hours": round(option.flight_outbound.duration_minutes / 60, 1),
                        "stops": option.flight_outbound.stops,
                        "deeplink": option.flight_outbound.deeplink
                    },
                    "return": {
                        "airline": option.flight_return.airline,
                        "price_per_person": option.flight_return.price_per_person,
                        "departure": option.flight_return.departure,
                        "arrival": option.flight_return.arrival,
                        "duration_hours": round(option.flight_return.duration_minutes / 60, 1),
                        "stops": option.flight_return.stops,
                        "deeplink": option.flight_return.deeplink
                    },
                    "total_flight_cost": option.flight_outbound.price_per_person + option.flight_return.price_per_person
                },
                "hotels": {
                    "mekka": {
                        "name": option.hotel_mekka.name,
                        "stars": option.hotel_mekka.stars,
                        "distance": option.hotel_mekka.distance_description,
                        "nights": option.hotel_mekka.nights,
                        "rooms_needed": option.hotel_mekka.rooms_needed,
                        "beds_per_room": option.hotel_mekka.beds_per_room,
                        "price_per_room_per_night": option.hotel_mekka.price_per_room_per_night,
                        "price_total": option.hotel_mekka.price_total,
                        "price_per_person": round(option.hotel_mekka.price_total / request.persons, 2),
                        "deeplink": option.hotel_mekka.deeplink,
                        "board": option.hotel_mekka.board
                    },
                    "medina": {
                        "name": option.hotel_medina.name,
                        "stars": option.hotel_medina.stars,
                        "distance": option.hotel_medina.distance_description,
                        "nights": option.hotel_medina.nights,
                        "rooms_needed": option.hotel_medina.rooms_needed,
                        "beds_per_room": option.hotel_medina.beds_per_room,
                        "price_per_room_per_night": option.hotel_medina.price_per_room_per_night,
                        "price_total": option.hotel_medina.price_total,
                        "price_per_person": round(option.hotel_medina.price_total / request.persons, 2),
                        "deeplink": option.hotel_medina.deeplink,
                        "board": option.hotel_medina.board
                    }
                },
                "pricing": {
                    "per_person": option.total_per_person,
                    "total_group": option.total_group,
                    "budget_fit_percent": option.budget_fit_percent,
                    "savings_amount": option.savings_amount,
                    "currency": "EUR"
                },
                "score": option.score,
                "recommendations": {
                    "why_recommended": f"Score: {option.score}/100 - Budget fit: {option.budget_fit_percent}%",
                    "booking_urgency": "Mock-Daten - Preise sind Beispielwerte",
                    "room_explanation": f"Hotels mit {option.hotel_mekka.beds_per_room}-Bett-Zimmern, {option.hotel_mekka.rooms_needed} Zimmer benötigt"
                }
            }
            frontend_options.append(frontend_option)
        
        # Prepare response
        response = MCPSearchResponse(
            success=True,
            lead_token=mcp_result.lead_token,
            options=frontend_options,
            meta={
                **mcp_result.meta,
                "frontend_integration": True,
                "search_method": "mcp_mock",
                "partner_apis_used": False,
                "4_bed_rule_applied": True,
                "mock_mode": True,
                "note": "Realistic mock data - partner APIs will be integrated later"
            },
            assumptions=mcp_result.assumptions,
            valid_until=mcp_result.valid_until,
            processing_time_ms=mcp_result.processing_time_ms,
            message=f"MOCK: Gefunden {len(frontend_options)} Optionen für {request.persons} Personen (Beispieldaten)"
        )
        
        # Log to Airtable (background task)
        background_tasks.add_task(
            log_mcp_search_to_airtable,
            request,
            response
        )
        
        logger.info(f"✅ MCP MOCK search completed: {len(frontend_options)} options found")
        return response
        
    except Exception as e:
        logger.error(f"❌ MCP MOCK search failed: {e}")
        capture_api_error(e, "mcp_mock_search", {
            "customer": f"{request.first_name} {request.last_name}",
            "budget": request.budget
        })
        
        # Return error response
        return MCPSearchResponse(
            success=False,
            lead_token=f"error_mock_{int(datetime.now().timestamp())}",
            options=[],
            meta={"error": str(e), "search_method": "mcp_mock"},
            assumptions={},
            valid_until=datetime.now().isoformat(),
            processing_time_ms=0,
            message=f"Mock search fehlgeschlagen: {str(e)}"
        )

async def log_mcp_search_to_airtable(
    request: FrontendLeadRequest, 
    result: MCPSearchResponse
):
    """Log MCP search results to Airtable for tracking"""
    try:
        airtable_data = {
            "Name": f"{request.first_name} {request.last_name}",
            "Email": request.email,
            "WhatsApp": request.whatsapp or "",
            "Budget": request.budget,
            "Persons": request.persons,
            "Departure Airport": request.departure_airport,
            "Departure Date": request.departure_date,
            "Lead Token": result.lead_token,
            "Options Found": len(result.options),
            "Best Price": result.options[0]["pricing"]["per_person"] if result.options else None,
            "Search Type": "MCP Mock",
            "Status": "Processed" if result.success else "Failed",
            "Processing Time": f"{result.processing_time_ms}ms",
            "Source": request.source,
            "Created": datetime.now().isoformat(),
            "Notes": f"MOCK DATA - {request.notes or ''}"
        }
        
        # Log using existing Airtable function
        await track_airtable_request("MCP_Mock_Search", airtable_data)
        logger.info(f"📊 Airtable logged (MOCK): {request.email}")
        
    except Exception as e:
        logger.error(f"📊 Airtable logging failed: {e}")

async def get_mcp_health_status_mock() -> Dict:
    """Get MCP system health status mit Mock providers"""
    try:
        # Test Mock providers
        provider_test = await MockProviderManager.test_all_providers()
        provider_status = MockProviderManager.get_provider_status()
        
        # Test budget allocator
        test_allocation = BudgetAllocator.allocate(1200, 4)
        
        # Test scoring engine
        test_score = ScoringEngine.calculate_score(
            {"avg_distance": 350, "budget_fit_percent": 95, "avg_rating": 4.2},
            {}
        )
        
        return {
            "status": "healthy",
            "mcp_version": "2.1.0",
            "mode": "mock_providers",
            "compliance": "Mock data - no external API calls",
            "features": {
                "budget_allocator": test_allocation is not None,
                "scoring_engine": test_score > 0,
                "4_bed_rule": True,
                "mock_providers": True,
                "deeplinks": True
            },
            "providers": provider_status,
            "test_results": {
                "budget_allocation": test_allocation,
                "scoring_test": test_score,
                "provider_test": provider_test
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"MCP health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }