"""
odoo-mcp-server entry point.

This is the FastMCP server scaffold. v1 will register five read-only tools
behind a defense-in-depth security gate. See the project README for the
full architecture and tool catalog:

    https://github.com/MrKhaled007/odoo-mcp-server

Current status: skeleton only. Tools and security guards land incrementally
through end of June 2026. Track the v1 checklist in the README "Roadmap"
section.
"""

from __future__ import annotations

import logging

# from fastmcp import FastMCP  # Will be wired up in the next milestone

logger = logging.getLogger(__name__)


def create_server() -> object:
    """
    Create and configure the MCP server.

    The actual implementation will:
        1. Load configuration via Pydantic Settings from environment variables.
        2. Initialize the security gate (auth, RBAC, whitelist, rate limit, audit).
        3. Initialize the Odoo client (read-only by default).
        4. Register tools, resources, and prompts through the security gate.
        5. Return the configured FastMCP instance.

    Returns:
        A FastMCP server instance, ready to serve over stdio.
    """
    logger.info("odoo-mcp-server: server scaffold loaded (v0.1.0.dev0)")
    logger.info("See README.md for the v1 roadmap and milestones.")
    raise NotImplementedError(
        "Server is in active development. v1 ships end of June 2026. "
        "See https://github.com/MrKhaled007/odoo-mcp-server for status."
    )


def main() -> None:
    """Entry point exposed via the project script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    server = create_server()
    # server.run()  # Will be enabled once the scaffold is wired up.


if __name__ == "__main__":
    main()
