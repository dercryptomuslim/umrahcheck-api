"""
Script to add MCP routes to existing umrahcheck_api_fixed.py
"""
import re

# MCP routes to add before the final routes
mcp_routes = '''
# ============= MCP AGENT INTEGRATION =============
# Added for compliance-first partner API search

from mcp_integration import (
    mcp_compliance_search,
    get_mcp_budget_analysis,
    get_mcp_health_status,
    FrontendLeadRequest,
    MCPSearchResponse
)

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

def add_mcp_routes():
    """Add MCP routes to existing API file"""
    
    # Read existing file
    with open('/Users/mustafaali/dev/umrahcheck-production/api/umrahcheck_api_fixed.py', 'r') as f:
        content = f.read()
    
    # Find insertion point (before @app.get("/") endpoint)
    pattern = r'(@app\.get\("/"\).*?def root.*?\n.*?\n.*?\n.*?\n.*?\n.*?\n.*?\n.*?\n.*?\n.*?\n.*?\n.*?\n.*?\n.*?\n.*?\n.*?\n.*?\n.*?\n.*?\n    \})'
    
    # Insert MCP routes before the root endpoint
    if '@app.get("/")' in content:
        # Find position before @app.get("/")
        parts = content.split('@app.get("/")')
        if len(parts) == 2:
            new_content = parts[0] + mcp_routes + '\n\n@app.get("/")" + parts[1]
            
            # Write updated file
            with open('/Users/mustafaali/dev/umrahcheck-production/api/umrahcheck_api_fixed.py', 'w') as f:
                f.write(new_content)
            
            print("✅ MCP routes added successfully!")
            return True
    
    print("❌ Could not find insertion point")
    return False

if __name__ == "__main__":
    add_mcp_routes()