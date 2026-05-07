"""
This module contains the MCP (Multi-Channel Processing) utilities for the LiveKit agent.
"""
from livekit.agents import mcp
from shared.core.config import settings

# Integrations MCP
def get_integrations_mcp(business_id: str):
    """Get MCP server instance for the given business ID."""
    return mcp.MCPServerHTTP(
        url=settings.MAIN_MCP_URL,
        headers={
            "Authorization": f"Bearer {settings.MAIN_MCP_KEY}",
            "X-Business-ID": business_id
        },
        transport_type='streamable_http',
        timeout=15,
        client_session_timeout_seconds=15
    )

def get_integrations_mcp_toolset(business_id: str):
    """Get a list of MCP tools for the given business ID."""
    return mcp.MCPToolset(id="integrations-mcp-toolset", mcp_server=get_integrations_mcp(business_id))
