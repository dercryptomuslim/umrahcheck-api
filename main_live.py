#!/usr/bin/env python3
"""
Main entry point for Railway deployment with MCP LIVE integration
Uses real-time data sources: Playwright scraper + RapidAPI + Airtable
"""
import os
import uvicorn

# Import the MCP-LIVE-integrated app
from umrahcheck_api_with_mcp_live import app

if __name__ == "__main__":
    # Railway deployment fix - handle PORT environment variable properly
    try:
        port = int(os.getenv("PORT", "8080"))
    except (ValueError, TypeError):
        port = 8080
    
    print(f"🚀 Starting UmrahCheck API with MCP LIVE Agent on port {port}")
    print("🔥 Using LIVE data sources:")
    print("   📊 Playwright scraper for live hotel prices")
    print("   ✈️ RapidAPI for flight data")
    print("   🏨 Airtable database for fallback")
    print("   💰 4-bed rule for accurate pricing")
    
    uvicorn.run(
        app,  # Direct app reference
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )