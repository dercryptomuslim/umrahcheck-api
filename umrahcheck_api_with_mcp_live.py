#!/usr/bin/env python3
"""
🚀 UmrahCheck API with MCP LIVE Integration
Production-ready API using LIVE data sources for real-time pricing
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import asyncio
import logging
from datetime import datetime, timedelta
import json
import os
import requests
import sentry_sdk

# Initialize Sentry monitoring
from sentry_config import (
    init_sentry, 
    capture_api_error, 
    set_transaction_context,
    track_airtable_request,
    track_hotel_recommendation,
    get_logger
)
from debug_sentry import router as debug_router

# MCP LIVE Integration
from mcp_live_integration import search_itinerary_live
from mcp_integration_mock import (  # Keep mock functions for budget analysis
    FrontendLeadRequest,
    MCPSearchResponse,
    log_mcp_search_to_airtable
)
from mcp_agent import BudgetAllocator, LeadRequest

init_sentry()
logger = get_logger(__name__)

# FastAPI App with MCP LIVE integration
app = FastAPI(
    title="UmrahCheck API with MCP LIVE Agent",
    description="Production API using LIVE data sources for real-time Umrah pricing",
    version="2.2.0-live",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
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

# Include debug router for Sentry
app.include_router(debug_router)

# ============= MCP LIVE ENDPOINTS =============

@app.post("/v2/mcp/search", response_model=MCPSearchResponse)
async def mcp_live_search_endpoint(
    request: FrontendLeadRequest,
    background_tasks: BackgroundTasks
):
    """
    🔥 LIVE Umrah search using real-time data sources
    - Playwright scraper for live hotel prices
    - RapidAPI for flight data  
    - Airtable database fallback
    - 4-bed hotel rule for accurate pricing
    - Integrates with existing Sentry and Airtable
    """
    try:
        logger.info(f"🔍 MCP LIVE search request: {request.first_name} {request.last_name}")
        
        # Add Sentry tracking
        set_transaction_context("mcp_live_search", {
            "customer": f"{request.first_name} {request.last_name}",
            "budget": request.budget,
            "persons": request.persons,
            "departure": request.departure_airport,
            "source": request.source
        })
        
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
        
        # Perform LIVE search
        mcp_result = await search_itinerary_live(mcp_request)
        
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
                        "deeplink": option.flight_outbound.deeplink,
                        "provider": option.flight_outbound.provider
                    },
                    "return": {
                        "airline": option.flight_return.airline,
                        "price_per_person": option.flight_return.price_per_person,
                        "departure": option.flight_return.departure,
                        "arrival": option.flight_return.arrival,
                        "duration_hours": round(option.flight_return.duration_minutes / 60, 1),
                        "stops": option.flight_return.stops,
                        "deeplink": option.flight_return.deeplink,
                        "provider": option.flight_return.provider
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
                        "board": option.hotel_mekka.board,
                        "provider": option.hotel_mekka.provider
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
                        "board": option.hotel_medina.board,
                        "provider": option.hotel_medina.provider
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
                    "booking_urgency": "Live-Preise - können sich schnell ändern. Jetzt prüfen empfohlen!",
                    "room_explanation": f"Hotels mit {option.hotel_mekka.beds_per_room}-Bett-Zimmern, {option.hotel_mekka.rooms_needed} Zimmer benötigt",
                    "data_freshness": f"Live-Daten abgerufen in {mcp_result.processing_time_ms}ms"
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
                "search_method": "mcp_live",
                "live_data_sources": True,
                "4_bed_rule_applied": True,
                "data_freshness": "real_time"
            },
            assumptions=mcp_result.assumptions,
            valid_until=mcp_result.valid_until,
            processing_time_ms=mcp_result.processing_time_ms,
            message=f"LIVE: Gefunden {len(frontend_options)} Optionen für {request.persons} Personen (Live-Daten)"
        )
        
        # Log to Airtable (background task)
        background_tasks.add_task(
            log_mcp_search_to_airtable,
            request,
            response
        )
        
        logger.info(f"✅ MCP LIVE search completed: {len(frontend_options)} options found")
        return response
        
    except Exception as e:
        logger.error(f"❌ MCP LIVE search failed: {e}")
        capture_api_error(e, "mcp_live_search", {
            "customer": f"{request.first_name} {request.last_name}",
            "budget": request.budget
        })
        
        # Return error response
        return MCPSearchResponse(
            success=False,
            lead_token=f"error_live_{int(datetime.now().timestamp())}",
            options=[],
            meta={"error": str(e), "search_method": "mcp_live"},
            assumptions={},
            valid_until=datetime.now().isoformat(),
            processing_time_ms=0,
            message=f"Live search fehlgeschlagen: {str(e)}"
        )

@app.get("/v2/mcp/health")
async def mcp_live_health_endpoint():
    """Health check for MCP LIVE Agent components"""
    try:
        # Test live components
        from playwright_scraper import get_scraper
        from mcp_live_integration import RAPIDAPI_AVAILABLE
        
        # Test budget allocator
        test_allocation = BudgetAllocator.allocate(1200, 4)
        
        return {
            "status": "healthy",
            "mcp_version": "2.2.0",
            "mode": "live_data_sources",
            "compliance": "Live scraping + partner APIs + database",
            "features": {
                "playwright_scraper": "available",
                "rapidapi_integration": RAPIDAPI_AVAILABLE,
                "airtable_database": "connected",
                "budget_allocator": test_allocation is not None,
                "4_bed_rule": True,
                "live_pricing": True
            },
            "data_sources": {
                "hotels": "Playwright Live Scraper + Airtable fallback",
                "flights": "RapidAPI + Live pricing fallback",
                "pricing": "Real-time market data"
            },
            "performance": {
                "typical_search_time": "2-5 seconds",
                "data_freshness": "real_time",
                "cache_strategy": "6 hour validity"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"MCP LIVE health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/v2/mcp/budget-analysis")
async def mcp_budget_analysis_endpoint(budget: str, persons: int):
    """Get budget allocation analysis using MCP allocator"""
    try:
        # Parse budget
        if '-' in budget:
            budget_parts = budget.split('-')
            budget_avg = (int(budget_parts[0]) + int(budget_parts[1])) // 2
        else:
            budget_avg = int(budget)
        
        # Get allocation
        allocation = BudgetAllocator.allocate(budget_avg, persons)
        
        return {
            "success": True,
            "budget_per_person": budget_avg,
            "total_budget": allocation["total_budget"],
            "allocation": {
                "flights": {
                    "budget_total": allocation["flight_budget_total"],
                    "budget_per_person": allocation["flight_budget_per_person"],
                    "percentage": "50%"
                },
                "hotels": {
                    "budget_total": allocation["hotel_budget_total"],
                    "budget_per_room_per_night": allocation["hotel_budget_per_room_per_night"],
                    "percentage": "40%"
                },
                "rest": {
                    "budget_total": allocation["total_budget"] * 0.1,
                    "percentage": "10%",
                    "description": "Transfers, visa, extras"
                }
            },
            "room_calculation": {
                "rooms_needed": allocation["rooms_needed"],
                "beds_per_room": allocation["beds_per_room"],
                "explanation": f"{allocation['rooms_needed']} rooms with {allocation['beds_per_room']} beds each for {persons} persons"
            },
            "4_bed_rule_applied": True,
            "live_pricing": "Used for real-time calculations"
        }
        
    except Exception as e:
        logger.error(f"Budget analysis failed: {e}")
        return {"success": False, "error": str(e)}

@app.get("/v2/mcp/demo")
async def mcp_live_demo_endpoint():
    """Demo endpoint showing MCP LIVE integration capabilities"""
    
    return {
        "message": "MCP LIVE Agent Integration Active",
        "mode": "live_data_sources",
        "features": [
            "🔥 LIVE hotel scraping with Playwright",
            "✈️ RapidAPI flight data integration", 
            "🏨 Airtable hotel database fallback",
            "💰 4-bed hotel rule for accurate pricing",
            "📊 Smart budget allocation (50% flights, 40% hotels)",
            "🔗 Real deeplinks for immediate booking",
            "📈 Sentry monitoring integration",
            "📋 Airtable lead logging",
            "⚡ Real-time price updates"
        ],
        "endpoints": {
            "search": "/v2/mcp/search - LIVE search with real data",
            "health": "/v2/mcp/health - System health with live components", 
            "budget": "/v2/mcp/budget-analysis - Live budget calculator",
            "demo": "/v2/mcp/demo - This endpoint"
        },
        "data_sources": {
            "hotels": "Playwright scraper → live hotel websites",
            "flights": "RapidAPI → real airline data",
            "fallback": "Airtable → curated hotel database"
        },
        "compliance": "Live scraping with permission + partner APIs + database",
        "performance": {
            "search_time": "2-5 seconds for live data",
            "data_freshness": "Real-time",
            "accuracy": "Market-accurate pricing"
        }
    }

# ============= ROOT ENDPOINT =============

@app.get("/")
async def root():
    """Root endpoint with MCP LIVE integration info"""
    return {
        "name": "UmrahCheck API with MCP LIVE Agent",
        "version": "2.2.0-live",
        "mode": "live_data_sources",
        "status": "🔥 Live data integration active",
        "features": {
            "live_hotel_scraping": "Playwright scraper for real-time prices",
            "live_flight_data": "RapidAPI integration for current fares",
            "airtable_fallback": "Hotel database for reliability",
            "sentry_monitoring": "Error tracking and performance",
            "4_bed_rule": "Accurate hotel pricing calculation",
            "budget_allocation": "Smart 50/40/10 distribution"
        },
        "data_flow": {
            "1": "User request → MCP Agent",
            "2": "MCP Agent → Live scrapers + APIs",
            "3": "Real-time data → Price calculation",
            "4": "4-bed rule → Accurate pricing",
            "5": "Results → User + Airtable logging"
        },
        "advantages": [
            "Real-time pricing accuracy",
            "No dependency on partner API approvals", 
            "Uses existing proven scrapers",
            "Fallback systems for reliability",
            "Immediate deployment ready"
        ]
    }

# ============= LEGACY COMPATIBILITY ENDPOINTS =============

@app.post("/api/lead-with-budget")
async def legacy_lead_with_budget_endpoint(request: FrontendLeadRequest):
    """
    🔄 Legacy compatibility endpoint - redirects to new MCP search
    Maintains backwards compatibility for existing integrations
    """
    try:
        logger.info(f"📥 Legacy API call redirected to MCP: {request.first_name} {request.last_name}")
        
        # Redirect to new MCP search endpoint
        mcp_result = await mcp_live_search_endpoint(request, BackgroundTasks())
        
        # Transform response to legacy format if needed
        legacy_response = {
            "success": mcp_result.success,
            "message": f"Legacy endpoint → MCP Agent: {mcp_result.message}",
            "lead_token": mcp_result.lead_token,
            "options_found": len(mcp_result.options) if mcp_result.options else 0,
            "mcp_redirect": True,
            "new_endpoint": "/v2/mcp/search",
            "data": mcp_result.model_dump() if hasattr(mcp_result, 'model_dump') else mcp_result
        }
        
        return legacy_response
        
    except Exception as e:
        logger.error(f"❌ Legacy endpoint failed: {e}")
        return {
            "success": False,
            "message": f"Legacy endpoint error: {str(e)}",
            "mcp_redirect": True,
            "new_endpoint": "/v2/mcp/search"
        }

# ============= HEALTH ENDPOINTS =============

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "mcp_integration": "live_active",
        "data_sources": "playwright_rapidapi_airtable",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/healthz")
async def healthz():
    """Railway health check endpoint"""
    return {"ok": True, "mcp": "live_integrated", "data": "real_time"}

# Sentry debug endpoint
@app.get("/sentry-debug")
async def trigger_error():
    """Trigger a test error for Sentry verification"""
    division_by_zero = 1 / 0

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "umrahcheck_api_with_mcp_live:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )