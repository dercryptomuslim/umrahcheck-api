#!/usr/bin/env python3
"""
🚀 UmrahCheck API with MCP Mock Integration
Production-ready API with Mock providers (until partner APIs available)
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

# MCP Mock Integration
from mcp_integration_mock import (
    mcp_compliance_search_mock,
    get_mcp_health_status_mock,
    FrontendLeadRequest,
    MCPSearchResponse
)
from mcp_mock_providers import MockProviderManager
from mcp_agent import BudgetAllocator

init_sentry()
logger = get_logger(__name__)

# Existing Pydantic Models (keeping original functionality)
class HotelPriceRequest(BaseModel):
    hotel_name: str = Field(..., description="Name des Hotels")
    city: str = Field(..., description="Stadt (Makkah oder Medina)")
    checkin_date: str = Field(..., description="Check-in Datum (YYYY-MM-DD)")
    checkout_date: str = Field(..., description="Check-out Datum (YYYY-MM-DD)")
    adults: int = Field(default=2, description="Anzahl Erwachsene")
    rooms: int = Field(default=1, description="Anzahl Zimmer")
    children: int = Field(default=0, description="Anzahl Kinder")
    currency: str = Field(default="EUR", description="Währung (EUR, USD, SAR)")

class CustomerRecommendationRequest(BaseModel):
    city: str = Field(..., description="Zielstadt")
    budget_category: str = Field(..., description="Budget-Kategorie")
    halal_required: bool = Field(default=True, description="Nur Halal-zertifizierte Hotels")

# FastAPI App with MCP Mock integration
app = FastAPI(
    title="UmrahCheck API with MCP Mock Agent",
    description="Production API with Mock providers for compliance-first search",
    version="2.1.0-mock",
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

# ============= MCP MOCK ENDPOINTS =============

@app.post("/v2/mcp/search", response_model=MCPSearchResponse)
async def mcp_search_endpoint(
    request: FrontendLeadRequest,
    background_tasks: BackgroundTasks
):
    """
    🔒 Compliance-first Umrah search using MOCK providers
    - Realistic hotel and flight data
    - Uses 4-bed hotel rule for realistic pricing
    - Integrates with existing Sentry and Airtable
    - Ready to switch to real partner APIs
    """
    try:
        logger.info(f"🔍 MCP MOCK search request: {request.first_name} {request.last_name}")
        result = await mcp_compliance_search_mock(request, background_tasks)
        
        if result.success:
            logger.info(f"✅ MCP MOCK search success: {len(result.options)} options")
        else:
            logger.warning(f"⚠️ MCP MOCK search failed: {result.message}")
            
        return result
        
    except Exception as e:
        logger.error(f"❌ MCP MOCK endpoint error: {e}")
        capture_api_error(e, "mcp_mock_endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v2/mcp/health")
async def mcp_health_endpoint():
    """Health check for MCP Mock Agent components"""
    return await get_mcp_health_status_mock()

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
            "4_bed_rule_applied": True
        }
        
    except Exception as e:
        logger.error(f"Budget analysis failed: {e}")
        return {"success": False, "error": str(e)}

@app.get("/v2/mcp/demo")
async def mcp_demo_endpoint():
    """Demo endpoint showing MCP Mock integration capabilities"""
    provider_status = MockProviderManager.get_provider_status()
    
    return {
        "message": "MCP Mock Agent Integration Active",
        "mode": "mock_providers",
        "features": [
            "Realistic flight and hotel mock data",
            "4-bed hotel rule for accurate pricing", 
            "Smart budget allocation (50% flights, 40% hotels)",
            "Deeplink generation for booking simulation",
            "Sentry monitoring integration",
            "Airtable logging integration",
            "Ready to switch to partner APIs"
        ],
        "endpoints": {
            "search": "/v2/mcp/search",
            "health": "/v2/mcp/health", 
            "budget": "/v2/mcp/budget-analysis",
            "demo": "/v2/mcp/demo",
            "providers": "/v2/mcp/providers"
        },
        "provider_status": provider_status,
        "compliance": "Mock data - no external API calls until partner APIs available",
        "next_steps": "Add DUFFEL_API_KEY, AMADEUS_API_KEY, HOTELBEDS_API_KEY to switch to real APIs"
    }

@app.get("/v2/mcp/providers")
async def mcp_providers_endpoint():
    """Get detailed provider status and test results"""
    try:
        provider_status = MockProviderManager.get_provider_status()
        test_results = await MockProviderManager.test_all_providers()
        
        return {
            "provider_status": provider_status,
            "test_results": test_results,
            "sample_data": {
                "flights": "6 airlines available (Saudia, Emirates, Turkish, Lufthansa, Qatar, Egyptair)",
                "hotels_makkah": "5 hotels (Fairmont Clock Tower, Conrad, Pullman, Makkah Towers, Al Masa)",
                "hotels_medina": "5 hotels (Movenpick, Shaza, Coral Al Ahsa, Al Aqeeq, Elaf Al Mashaer)",
                "price_ranges": "€70-220 per room per night, €350-500 per person flights"
            },
            "data_quality": "Realistic prices based on 2024/2025 market research"
        }
    except Exception as e:
        logger.error(f"Provider status check failed: {e}")
        return {"error": str(e)}

# ============= ROOT ENDPOINT =============

@app.get("/")
async def root():
    """Root endpoint with MCP Mock integration info"""
    return {
        "name": "UmrahCheck API with MCP Mock Agent",
        "version": "2.1.0-mock",
        "mode": "mock_providers",
        "status": "Ready for partner API integration",
        "features": {
            "mcp_mock_search": "Realistic mock data for development/testing",
            "airtable_integration": "Full logging and tracking",
            "sentry_monitoring": "Error tracking and performance",
            "4_bed_rule": "Accurate hotel pricing calculation",
            "budget_allocation": "Smart 50/40/10 distribution"
        },
        "endpoints": {
            "mcp_v2": [
                "/v2/mcp/search - Main search endpoint with mock data",
                "/v2/mcp/health - System health and provider status",
                "/v2/mcp/budget-analysis - Budget allocation calculator",
                "/v2/mcp/demo - Feature demonstration",
                "/v2/mcp/providers - Provider status and test data"
            ]
        },
        "next_steps": [
            "Set partner API keys in Railway environment",
            "Switch from mock to real providers",
            "Frontend integration testing",
            "Production deployment validation"
        ],
        "compliance": "Mock data only - no external API calls"
    }

# ============= HEALTH ENDPOINTS =============

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "mcp_integration": "active",
        "mode": "mock_providers",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/healthz")
async def healthz():
    """Railway health check endpoint"""
    return {"ok": True, "mcp": "mock_integrated"}

# Sentry debug endpoint
@app.get("/sentry-debug")
async def trigger_error():
    """Trigger a test error for Sentry verification"""
    division_by_zero = 1 / 0

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "umrahcheck_api_with_mcp_mock:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )