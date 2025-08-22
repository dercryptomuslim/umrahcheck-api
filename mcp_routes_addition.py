"""
Manual addition of MCP routes to umrahcheck_api_fixed.py
Insert this code before the @app.get("/") root endpoint
"""

MCP_IMPORTS = '''
# ============= MCP AGENT INTEGRATION =============
from mcp_integration import (
    mcp_compliance_search,
    get_mcp_budget_analysis,
    get_mcp_health_status,
    FrontendLeadRequest,
    MCPSearchResponse
)
'''

MCP_ROUTES = '''
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

'''

def manual_integration_instructions():
    """Print manual integration instructions"""
    print("🔧 MANUAL MCP INTEGRATION INSTRUCTIONS")
    print("=====================================")
    print()
    print("1. Add imports after existing imports in umrahcheck_api_fixed.py:")
    print(MCP_IMPORTS)
    print()
    print("2. Add routes before @app.get('/') root endpoint:")
    print(MCP_ROUTES)
    print()
    print("3. Update requirements.txt:")
    print("aioredis==2.0.1")
    print("python-jose[cryptography]==3.3.0")
    print("httpx==0.25.2")
    print()
    print("4. Add environment variables to Railway:")
    print("MCP_API_KEY=umrahcheck_mcp_2025_secure")
    print("DUFFEL_API_KEY=your_duffel_key")
    print("AMADEUS_API_KEY=your_amadeus_key")
    print("HOTELBEDS_API_KEY=your_hotelbeds_key")

if __name__ == "__main__":
    manual_integration_instructions()