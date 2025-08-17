#!/usr/bin/env python3
"""
Main entry point for Railway deployment
"""
import os
import uvicorn

# Import the Airtable API app
from umrahcheck_api_fixed import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )