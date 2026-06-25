"""
Odoo client wrapper for odoo-mcp-server.

This module is the ONLY place in the codebase that speaks XML-RPC to
Odoo. Every tool, resource, and security guard above this layer calls
methods on `OdooClient` instead of touching `xmlrpc.client` directly.

The class exposes two layers:

  1. Connection & authentication (called once at startup):
       - __init__()       -> store connection details
       - from_settings()  -> alternative constructor from Settings
       - authenticate()   -> call Odoo, cache the uid

  2. Operations (called many times during normal use):
       - search()         -> return matching record IDs
       - read()           -> return field data for given IDs
       - search_read()    -> the workhorse: filter + fetch in one call
       - search_count()   -> just the count, no data
"""

from __future__ import annotations

import logging
import xmlrpc.client
from typing import Any

from odoo_mcp.config import Settings

logger = logging.getLogger(__name__)


class OdooAuthenticationError(Exception):
    """Raised when Odoo refuses our credentials."""


class OdooClient:
    """..."""
    # ... existing code continues





class OdooClient:
    """
    A thin wrapper around Odoo's XML-RPC interface.

    The client holds the URL, database, username, and API key, plus two
    XML-RPC ServerProxy objects (one for the `common` endpoint, one for
    the `object` endpoint). After `authenticate()` runs, the user ID is
    cached on the instance and used by every subsequent operation.

    Instances are not safe to share across threads as written. For v1
    we use a single instance from a single thread.
    """

    def __init__(
        self,
        url: str,
        database: str,
        username: str,
        api_key: str,
    ) -> None:
        # Connection details, stored for later use.
        self._url = url.rstrip("/")
        self._database = database
        self._username = username
        self._api_key = api_key

        # Two XML-RPC endpoints exposed by Odoo:
        #   /xmlrpc/2/common -> authentication and version info
        #   /xmlrpc/2/object -> all ORM method calls (search, read, etc.)
        self._common = xmlrpc.client.ServerProxy(f"{self._url}/xmlrpc/2/common")
        self._models = xmlrpc.client.ServerProxy(f"{self._url}/xmlrpc/2/object")

        # The Odoo user ID, set by authenticate(). Until then we're not
        # authenticated and no operations will work.
        self._uid: int | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> OdooClient:
        """
        Build an OdooClient from a Settings object.

        This is the convenience constructor used by production code that
        already has a Settings instance handy. Tests typically use
        __init__ directly with hand-crafted values.
        """
        return cls(
            url=settings.odoo_url,
            database=settings.odoo_db,
            username=settings.odoo_username,
            api_key=settings.odoo_api_key,
        )
    
    def authenticate(self) -> int:
        """
        Authenticate against Odoo and cache the user ID.

        This is a one-shot operation called once at server startup. Odoo
        does a database lookup and credential check on every call to
        `common.authenticate`, so we run it exactly once and reuse the
        returned uid for all subsequent operations.

        Returns:
            The authenticated user's integer ID (uid).

        Raises:
            OdooAuthenticationError: If Odoo rejects the credentials.
            xmlrpc.client.Fault: If Odoo returns a protocol-level error.
        """
        logger.info(
            "Authenticating against Odoo at %s as %s",
            self._url,
            self._username,
        )

        # Odoo's authenticate signature: (db, username, password_or_key, user_agent_env)
        # The fourth argument is a dict that older Odoo versions used for
        # user-agent info. Modern Odoo ignores it but still requires it
        # be present, so we pass an empty dict.
        uid = self._common.authenticate(
            self._database,
            self._username,
            self._api_key,
            {},
        )

        # Odoo returns:
        #   - an integer uid on success
        #   - False (literal) on failure
        # We normalise the failure case into a real exception so callers
        # don't have to guard against the False sentinel.
        if not uid:
            raise OdooAuthenticationError(
                f"Authentication failed for user {self._username!r} "
                f"on database {self._database!r}"
            )

        logger.info("Authenticated as uid=%d", uid)
        self._uid = uid
        return uid
    
    def _ensure_authenticated(self) -> int:
        """
        Return the cached uid or raise if we haven't authenticated yet.

        Every operation method calls this as a first guard so we get a
        clear error if someone tries to use the client before
        `authenticate()` has been called.
        """
        if self._uid is None:
            raise RuntimeError(
                "OdooClient.authenticate() must be called before any operation."
            )
        return self._uid

    def search(
        self,
        model: str,
        domain: list,
        limit: int | None = None,
        offset: int = 0,
        order: str | None = None,
    ) -> list[int]:
        """
        Return IDs of records matching the domain.

        Args:
            model: The Odoo model name, e.g. "res.partner".
            domain: An Odoo domain filter, e.g. [["is_company", "=", True]].
            limit: Maximum number of IDs to return. None means no limit.
            offset: How many records to skip (for pagination).
            order: Sort expression, e.g. "create_date desc".

        Returns:
            A list of integer record IDs.
        """
        uid = self._ensure_authenticated()
        kwargs: dict[str, Any] = {"offset": offset}
        if limit is not None:
            kwargs["limit"] = limit
        if order is not None:
            kwargs["order"] = order

        logger.debug("search(model=%s, domain=%s, kwargs=%s)", model, domain, kwargs)
        return self._models.execute_kw(
            self._database,
            uid,
            self._api_key,
            model,
            "search",
            [domain],
            kwargs,
        )

    def read(
        self,
        model: str,
        ids: list[int],
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return field data for a list of record IDs.

        Args:
            model: The Odoo model name.
            ids: A list of record IDs to read.
            fields: Which fields to return. None means all readable fields
                (not recommended in production — always pass a whitelist).

        Returns:
            A list of dicts, one per record, with the requested fields.
        """
        uid = self._ensure_authenticated()
        kwargs: dict[str, Any] = {}
        if fields is not None:
            kwargs["fields"] = fields

        logger.debug("read(model=%s, ids=%s, fields=%s)", model, ids, fields)
        return self._models.execute_kw(
            self._database,
            uid,
            self._api_key,
            model,
            "read",
            [ids],
            kwargs,
        )

    def search_read(
        self,
        model: str,
        domain: list,
        fields: list[str] | None = None,
        limit: int | None = None,
        offset: int = 0,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search and read in one round-trip.

        The workhorse method. Equivalent to `search` followed by `read`,
        but cheaper because it makes a single XML-RPC call and lets Odoo
        execute it as a single database query.

        Args:
            model: The Odoo model name.
            domain: An Odoo domain filter.
            fields: Which fields to return. Always pass a whitelist.
            limit: Maximum number of records to return.
            offset: Pagination offset.
            order: Sort expression.

        Returns:
            A list of dicts, one per matching record.
        """
        uid = self._ensure_authenticated()
        kwargs: dict[str, Any] = {"offset": offset}
        if fields is not None:
            kwargs["fields"] = fields
        if limit is not None:
            kwargs["limit"] = limit
        if order is not None:
            kwargs["order"] = order

        logger.debug(
            "search_read(model=%s, domain=%s, kwargs=%s)",
            model,
            domain,
            kwargs,
        )
        return self._models.execute_kw(
            self._database,
            uid,
            self._api_key,
            model,
            "search_read",
            [domain],
            kwargs,
        )

    def search_count(self, model: str, domain: list) -> int:
        """
        Return the count of records matching the domain.

        Lightweight alternative to `search` when you only need a number.
        No record data is loaded into memory, so this is the right call
        for "how many invoices do we have?" style questions.

        Args:
            model: The Odoo model name.
            domain: An Odoo domain filter.

        Returns:
            The count of matching records.
        """
        uid = self._ensure_authenticated()

        logger.debug("search_count(model=%s, domain=%s)", model, domain)
        return self._models.execute_kw(
            self._database,
            uid,
            self._api_key,
            model,
            "search_count",
            [domain],
        )
