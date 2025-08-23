#!/usr/bin/env python3
"""
🔥 FORCE MCP LIVE: Main entry point for Railway deployment with MCP LIVE integration
Uses real-time data sources: Playwright scraper + RapidAPI + Airtable
Updated: 2025-08-23 - Force Live System Activation
"""
import os
import uvicorn

# 🚨 FORCE IMPORT: MCP-LIVE-integrated app (v2.2.0-live)
from umrahcheck_api_with_mcp_live import app

# Verify we're importing the correct live app
print(f"🔥 LIVE APP VERIFICATION:")
print(f"   📱 App Title: {app.title}")
print(f"   🚀 App Version: {app.version}")
print(f"   📊 Expected: UmrahCheck API with MCP LIVE Agent v2.2.0-live")

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