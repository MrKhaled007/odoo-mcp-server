"""
Partner (contact) tools for odoo-mcp-server.

Exposes read-only tools over Odoo's `res.partner` model — customers,
vendors, and companies. Registered with the MCP server via `register()`.
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from odoo_mcp.config import Settings
from odoo_mcp.odoo_client import OdooClient

logger = logging.getLogger(__name__)

# The only fields this tool is allowed to return. This is a whitelist:
# anything not in this list can never leak through the tool, even by
# accident. A first small piece of the security model.
_PARTNER_FIELDS = [
    "id",
    "name",
    "email",
    "phone",
    "city",
    "country_id",
    "is_company",
    "customer_rank",
    "supplier_rank",
]


def register(mcp: FastMCP, client: OdooClient, settings: Settings) -> None:
    """
    Register partner tools on the given MCP server.

    Args:
        mcp: The FastMCP server instance.
        client: An authenticated Odoo client.
        settings: Server settings (used for record caps, etc.).
    """

    @mcp.tool()
    def search_partners(
        name: str | None = None,
        companies_only: bool = False,
        limit: int = 20,
    ) -> list[dict]:
        """
        Search Odoo contacts (customers, vendors, companies).

        Args:
            name: Optional text to match against the contact's name
                (case-insensitive, partial match).
            companies_only: If true, return only companies (not individuals).
            limit: Maximum number of contacts to return (capped by server config).

        Returns:
            A list of contacts, each with name, email, phone, city, country,
            and whether it is a company.
        """
        # Enforce the server's hard cap regardless of what was requested.
        effective_limit = min(limit, settings.mcp_max_records)

        # Build the Odoo domain filter from the inputs.
        domain: list = []
        if name:
            domain.append(["name", "ilike", name])
        if companies_only:
            domain.append(["is_company", "=", True])

        logger.info(
            "search_partners(name=%r, companies_only=%s, limit=%d)",
            name,
            companies_only,
            effective_limit,
        )

        results = client.search_read(
            model="res.partner",
            domain=domain,
            fields=_PARTNER_FIELDS,
            limit=effective_limit,
            order="name asc",
        )
        return results

    logger.info("Registered partner tools")