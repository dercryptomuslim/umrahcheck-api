#!/usr/bin/env python3
"""
Main entry point for Railway deployment
"""
import os
import uvicorn

# Import the Airtable API app
from umrahcheck_api_fixed import app

if __name__ == "__main__":
    # Railway deployment fix - handle PORT environment variable properly
    try:
        port = int(os.getenv("PORT", "8080"))
    except (ValueError, TypeError):
        port = 8080
    
    print(f"🚀 Starting UmrahCheck API on port {port}")
    
    uvicorn.run(
        app,  # Direct app reference instead of string
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )