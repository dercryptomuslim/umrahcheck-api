"""
MCP Agent Integration für bestehende UmrahCheck Production API
Compliance-first search with partner APIs
"""
from fastapi import HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
import logging
from datetime import datetime
import asyncio

# Import MCP Agent components
from mcp_agent import (
    search_itinerary,
    LeadRequest, 
    ItineraryResponse,
    BudgetAllocator,
    ScoringEngine,
    FlightProvider,
    HotelProvider
)

# Sentry integration
from sentry_config import (
    capture_api_error, 
    set_transaction_context,
    track_airtable_request,
    get_logger
)

logger = get_logger(__name__)

# Extended models für Frontend Integration
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

async def mcp_compliance_search(
    request: FrontendLeadRequest,
    background_tasks: BackgroundTasks
) -> MCPSearchResponse:
    """
    🔒 Compliance-first Umrah search using partner APIs only
    Integrated with existing Sentry and Airtable systems
    """
    try:
        # Add Sentry tracking
        set_transaction_context("mcp_search", {
            "customer": f"{request.first_name} {request.last_name}",
            "budget": request.budget,
            "persons": request.persons,
            "departure": request.departure_airport,
            "source": request.source
        })
        
        logger.info(f"🔍 MCP search started for {request.first_name} {request.last_name}")
        
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
        
        # Perform MCP search
        mcp_result = await search_itinerary(mcp_request)
        
        # Convert options für Frontend-friendly format
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
                        "price_per_person": option.hotel_mekka.price_total / request.persons,
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
                        "price_per_person": option.hotel_medina.price_total / request.persons,
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
                    "booking_urgency": "Preise können sich täglich ändern. Jetzt buchen empfohlen.",
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
                "search_method": "mcp_compliance",
                "partner_apis_used": True,
                "4_bed_rule_applied": True
            },
            assumptions=mcp_result.assumptions,
            valid_until=mcp_result.valid_until,
            processing_time_ms=mcp_result.processing_time_ms,
            message=f"Gefunden: {len(frontend_options)} Optionen für {request.persons} Personen"
        )
        
        # Log to Airtable (background task)
        background_tasks.add_task(
            log_mcp_search_to_airtable,
            request,
            response
        )
        
        logger.info(f"✅ MCP search completed: {len(frontend_options)} options found")
        return response
        
    except Exception as e:
        logger.error(f"❌ MCP search failed: {e}")
        capture_api_error(e, "mcp_search", {
            "customer": f"{request.first_name} {request.last_name}",
            "budget": request.budget
        })
        
        # Return error response
        return MCPSearchResponse(
            success=False,
            lead_token=f"error_{int(datetime.now().timestamp())}",
            options=[],
            meta={"error": str(e), "search_method": "mcp_compliance"},
            assumptions={},
            valid_until=datetime.now().isoformat(),
            processing_time_ms=0,
            message=f"Suche fehlgeschlagen: {str(e)}"
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
            "Search Type": "MCP Compliance",
            "Status": "Processed" if result.success else "Failed",
            "Processing Time": f"{result.processing_time_ms}ms",
            "Source": request.source,
            "Created": datetime.now().isoformat(),
            "Notes": request.notes or ""
        }
        
        # Log using existing Airtable function
        await track_airtable_request("MCP_Search", airtable_data)
        logger.info(f"📊 Airtable logged: {request.email}")
        
    except Exception as e:
        logger.error(f"📊 Airtable logging failed: {e}")

def get_mcp_budget_analysis(budget_str: str, persons: int) -> Dict:
    """Get budget analysis using MCP allocator"""
    try:
        # Parse budget
        if '-' in budget_str:
            budget_parts = budget_str.split('-')
            budget_avg = (int(budget_parts[0]) + int(budget_parts[1])) // 2
        else:
            budget_avg = int(budget_str)
        
        # Get allocation
        allocation = BudgetAllocator.allocate(budget_avg, persons)
        
        return {
            "budget_per_person": budget_avg,
            "total_budget": allocation["total_budget"],
            "flight_budget": allocation["flight_budget_total"],
            "hotel_budget": allocation["hotel_budget_total"],
            "rooms_needed": allocation["rooms_needed"],
            "beds_per_room": allocation["beds_per_room"],
            "allocation_strategy": "50% flights, 40% hotels, 10% rest"
        }
        
    except Exception as e:
        logger.error(f"Budget analysis failed: {e}")
        return {"error": str(e)}

async def get_mcp_health_status() -> Dict:
    """Get MCP system health status"""
    try:
        # Test budget allocator
        test_allocation = BudgetAllocator.allocate(1200, 4)
        
        # Test scoring engine
        test_score = ScoringEngine.calculate_score(
            {"avg_distance": 350, "budget_fit_percent": 95, "avg_rating": 4.2},
            {}
        )
        
        return {
            "status": "healthy",
            "mcp_version": "2.0.0",
            "compliance": "Partner APIs only",
            "features": {
                "budget_allocator": test_allocation is not None,
                "scoring_engine": test_score > 0,
                "4_bed_rule": True,
                "partner_apis": True,
                "deeplinks": True
            },
            "test_results": {
                "budget_allocation": test_allocation,
                "scoring_test": test_score
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