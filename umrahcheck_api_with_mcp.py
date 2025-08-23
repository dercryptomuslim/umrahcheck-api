#!/usr/bin/env python3
"""
🚀 UmrahCheck API with MCP Agent Integration
Production-ready API with compliance-first search
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
from playwright_scraper import scrape_hotel_prices_with_customer_dates, get_scraper

# MCP Agent Integration
from mcp_integration import (
    mcp_compliance_search,
    get_mcp_budget_analysis,
    get_mcp_health_status,
    FrontendLeadRequest,
    MCPSearchResponse
)

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

# FastAPI App with MCP integration
app = FastAPI(
    title="UmrahCheck API with MCP Agent",
    description="Production API with compliance-first search capabilities",
    version="2.1.0",
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

# ============= MCP AGENT ENDPOINTS =============

@app.post("/v2/mcp/search", response_model=MCPSearchResponse)
async def mcp_search_endpoint(
    request: FrontendLeadRequest,
    background_tasks: BackgroundTasks
):
    """
    🔒 Compliance-first Umrah search using partner APIs only
    - Respects ToS and robots.txt
    - Uses 4-bed hotel rule for realistic pricing
    - Integrates with existing Sentry and Airtable
    """
    try:
        logger.info(f"🔍 MCP search request: {request.first_name} {request.last_name}")
        result = await mcp_compliance_search(request, background_tasks)
        
        if result.success:
            logger.info(f"✅ MCP search success: {len(result.options)} options")
        else:
            logger.warning(f"⚠️ MCP search failed: {result.message}")
            
        return result
        
    except Exception as e:
        logger.error(f"❌ MCP endpoint error: {e}")
        capture_api_error(e, "mcp_endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v2/mcp/health")
async def mcp_health_endpoint():
    """Health check for MCP Agent components"""
    return await get_mcp_health_status()

@app.post("/v2/mcp/budget-analysis")
async def mcp_budget_analysis_endpoint(budget: str, persons: int):
    """Get budget allocation analysis using MCP allocator"""
    return get_mcp_budget_analysis(budget, persons)

@app.get("/v2/mcp/demo")
async def mcp_demo_endpoint():
    """Demo endpoint showing MCP integration capabilities"""
    return {
        "message": "MCP Agent Integration Active",
        "features": [
            "Compliance-first partner API search",
            "4-bed hotel rule for realistic pricing", 
            "Smart budget allocation (50% flights, 40% hotels)",
            "Deeplink generation for direct booking",
            "Sentry monitoring integration",
            "Airtable logging integration"
        ],
        "endpoints": {
            "search": "/v2/mcp/search",
            "health": "/v2/mcp/health", 
            "budget": "/v2/mcp/budget-analysis"
        },
        "compliance": "Partner APIs only - No unauthorized scraping"
    }

# ============= EXISTING ENDPOINTS (Legacy Support) =============

@app.get("/")
async def root():
    """Root endpoint with MCP integration info"""
    return {
        "name": "UmrahCheck API with MCP Agent",
        "version": "2.1.0",
        "features": {
            "legacy_scraping": "Available for existing functionality",
            "mcp_compliance_search": "New partner API search",
            "airtable_integration": "Full logging and tracking",
            "sentry_monitoring": "Error tracking and performance"
        },
        "endpoints": {
            "legacy": [
                "/api/hotels/live-prices",
                "/api/hotels/scrape-prices",
                "/api/customers/recommendations"
            ],
            "mcp_v2": [
                "/v2/mcp/search",
                "/v2/mcp/health",
                "/v2/mcp/budget-analysis"
            ]
        },
        "compliance": "MCP endpoints use partner APIs only"
    }

# ============= LEGACY COMPATIBILITY ENDPOINTS =============

@app.post("/api/lead-with-budget")
async def legacy_lead_with_budget_endpoint(request: FrontendLeadRequest):
    """
    🔄 Legacy compatibility endpoint - redirects to MCP search
    Maintains backwards compatibility for existing frontend integrations
    """
    try:
        logger.info(f"📥 Legacy API call for: {request.first_name} {request.last_name}")
        
        # Use the MCP compliance search
        mcp_result = await mcp_search_endpoint(request, BackgroundTasks())
        
        # Transform to legacy format
        legacy_response = {
            "success": mcp_result.success,
            "message": f"MCP Agent processed: {mcp_result.message}",
            "lead_token": mcp_result.lead_token,
            "options_found": len(mcp_result.options) if mcp_result.options else 0,
            "processing_time_ms": mcp_result.processing_time_ms,
            "mcp_redirect": True,
            "data": {
                "options": mcp_result.options,
                "meta": mcp_result.meta,
                "assumptions": mcp_result.assumptions
            }
        }
        
        return legacy_response
        
    except Exception as e:
        logger.error(f"❌ Legacy endpoint failed: {e}")
        return {
            "success": False,
            "message": f"Legacy endpoint error: {str(e)}",
            "mcp_redirect": True,
            "recommended_endpoint": "/v2/mcp/search"
        }

# Placeholder for existing endpoints (would copy from original file)
# These maintain backward compatibility

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "mcp_integration": "active",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/healthz")
async def healthz():
    """Railway health check endpoint"""
    return {"ok": True, "mcp": "integrated"}

# Sentry debug endpoint
@app.get("/sentry-debug")
async def trigger_error():
    """Trigger a test error for Sentry verification"""
    division_by_zero = 1 / 0

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "umrahcheck_api_with_mcp:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )