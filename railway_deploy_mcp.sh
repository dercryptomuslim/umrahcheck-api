#!/bin/bash
"""
Railway Deployment Script für MCP Integration
"""

echo "🚀 UmrahCheck MCP Integration - Railway Deployment"
echo "================================================="

# Check if we're in the right directory
if [ ! -f "umrahcheck_api_with_mcp.py" ]; then
    echo "❌ Error: umrahcheck_api_with_mcp.py not found"
    echo "Please run this script from the api directory"
    exit 1
fi

# Backup current main.py
if [ -f "main.py" ]; then
    cp main.py main_backup.py
    echo "✅ Backed up existing main.py"
fi

# Update main.py to use MCP integration
cat > main.py << 'EOF'
#!/usr/bin/env python3
"""
Main entry point for Railway deployment with MCP integration
"""
import os
import uvicorn

# Import the MCP-integrated app
from umrahcheck_api_with_mcp import app

if __name__ == "__main__":
    # Railway deployment fix - handle PORT environment variable properly
    try:
        port = int(os.getenv("PORT", "8080"))
    except (ValueError, TypeError):
        port = 8080
    
    print(f"🚀 Starting UmrahCheck API with MCP Agent on port {port}")
    
    uvicorn.run(
        app,  # Direct app reference
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
EOF

echo "✅ Updated main.py for MCP integration"

# Update requirements.txt
cp requirements_mcp.txt requirements.txt
echo "✅ Updated requirements.txt with MCP dependencies"

# Check environment variables
echo ""
echo "🔧 Environment Variables Required:"
echo "================================="
echo "MCP_API_KEY=umrahcheck_mcp_2025_secure"
echo "DUFFEL_API_KEY=your_duffel_key"
echo "AMADEUS_API_KEY=your_amadeus_key"
echo "HOTELBEDS_API_KEY=your_hotelbeds_key"
echo "AIRTABLE_TOKEN=your_existing_token"
echo "SENTRY_DSN=your_existing_dsn"
echo ""

# Git commands for deployment
echo "📦 Git Deployment Commands:"
echo "==========================="
echo "git add ."
echo "git commit -m '🔗 MCP Agent Integration - Compliance-first search v2.1.0'"
echo "git push railway main"
echo ""

# Health check commands
echo "🏥 Post-Deployment Health Checks:"
echo "=================================="
echo "curl https://umrahcheck-api-production.up.railway.app/health"
echo "curl https://umrahcheck-api-production.up.railway.app/v2/mcp/health"
echo "curl https://umrahcheck-api-production.up.railway.app/v2/mcp/demo"
echo ""

echo "✅ MCP Integration ready for Railway deployment!"
echo ""
echo "Next steps:"
echo "1. Set environment variables in Railway dashboard"
echo "2. Run git commands above to deploy"
echo "3. Test health endpoints"
echo "4. Update frontend to use /v2/mcp/search"