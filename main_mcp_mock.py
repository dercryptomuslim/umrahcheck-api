#!/usr/bin/env python3
"""
Main entry point for Railway deployment with MCP Mock integration
"""
import os
import uvicorn

# Import the MCP-Mock-integrated app
from umrahcheck_api_with_mcp_mock import app

if __name__ == "__main__":
    # Railway deployment fix - handle PORT environment variable properly
    try:
        port = int(os.getenv("PORT", "8080"))
    except (ValueError, TypeError):
        port = 8080
    
    print(f"🚀 Starting UmrahCheck API with MCP Mock Agent on port {port}")
    print("📊 Using realistic mock data until partner APIs are configured")
    
    uvicorn.run(
        app,  # Direct app reference
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )