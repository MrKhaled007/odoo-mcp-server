"""
Entry point for odoo-mcp-server.

Creates the FastMCP server, wires up the Odoo client, registers each
tool module, and starts serving over stdio so MCP clients (Claude
Desktop, Copilot, Cursor) can connect.

Run directly:
    python -m odoo_mcp.server

Or via the installed script:
    odoo-mcp-server
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from odoo_mcp.config import get_settings
from odoo_mcp.odoo_client import OdooClient
from odoo_mcp.tools import partners

logger = logging.getLogger(__name__)


def create_server() -> FastMCP:
    """
    Build and configure the MCP server.

    Steps:
      1. Load settings from environment / .env.
      2. Create and authenticate the Odoo client once at startup.
      3. Create the FastMCP instance.
      4. Register each tool module, handing it the authenticated client.

    Returns:
        A configured FastMCP instance, ready to run.
    """
    settings = get_settings()

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    logger.info("Starting odoo-mcp-server")

    # Create the Odoo client and authenticate once, at startup.
    client = OdooClient.from_settings(settings)
    client.authenticate()

    # Create the MCP server.
    mcp = FastMCP("odoo-mcp-server")

    # Register each tool module. Each register() call attaches its tools
    # to the server, closing over the shared, authenticated client.
    partners.register(mcp, client, settings)

    logger.info("odoo-mcp-server ready")
    return mcp


def main() -> None:
    """Console-script entry point: build the server and serve over stdio."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()