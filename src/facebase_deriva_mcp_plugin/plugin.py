from __future__ import annotations

"""FaceBase plugin entry point.

Declares the RAG sources and dataset indexer for the FaceBase catalog. Called
automatically by deriva-mcp-core's plugin loader when this package is installed
and DERIVA_MCP_RAG_ENABLED=true.

register(ctx) is a no-op for any RAG declarations when DERIVA_MCP_RAG_ENABLED=false,
so no guard logic is needed here -- the PluginContext handles it.

Configuration (via deriva-mcp.env or environment variables):

  FACEBASE_DERIVA_MCP_PLUGIN_HOSTNAME                 FaceBase server hostname (default: www.facebase.org)
  FACEBASE_DERIVA_MCP_PLUGIN_CATALOG_ID               ERMrest catalog ID (default: 1)
  FACEBASE_DERIVA_MCP_PLUGIN_MAX_INDEXED_WEB_PAGES    Max pages to crawl (default: 300)
  FACEBASE_DERIVA_MCP_PLUGIN_MAX_INDEXED_DATASET_RECORDS  Max dataset rows to index; omit for no limit (default: unset)
"""

from typing import TYPE_CHECKING

from .enricher import enrich_dataset
from . import prompts as _prompts

if TYPE_CHECKING:
    from deriva_mcp_core.plugin.api import PluginContext

_DEFAULT_HOSTNAME = "www.facebase.org"
_DEFAULT_CATALOG_ID = "1"
_DEFAULT_MAX_INDEXED_WEB_PAGES = 300


def register(ctx: PluginContext) -> None:
    """Register FaceBase tools, prompts, and RAG sources with the MCP server."""

    hostname = ctx.env.get("FACEBASE_DERIVA_MCP_PLUGIN_HOSTNAME", _DEFAULT_HOSTNAME)
    max_web_pages = int(ctx.env.get("FACEBASE_DERIVA_MCP_PLUGIN_MAX_INDEXED_WEB_PAGES", str(_DEFAULT_MAX_INDEXED_WEB_PAGES)))
    max_records_str = ctx.env.get("FACEBASE_DERIVA_MCP_PLUGIN_MAX_INDEXED_DATASET_RECORDS")
    max_records = int(max_records_str) if max_records_str else None

    # ------------------------------------------------------------------
    # RAG: FaceBase website content
    # ------------------------------------------------------------------
    ctx.rag_web_source(
        name="facebase-web",
        base_url=f"https://{hostname}",
        max_pages=max_web_pages,
        doc_type="web-content",
        include_path_prefix="/",
        rate_limit_seconds=1.0,
    )

    # ------------------------------------------------------------------
    # RAG: FaceBase dataset records (enriched from ERMrest catalog)
    # ------------------------------------------------------------------
    catalog_id = ctx.env.get("FACEBASE_DERIVA_MCP_PLUGIN_CATALOG_ID", _DEFAULT_CATALOG_ID)
    ctx.rag_dataset_indexer(
        schema="isa",
        table="dataset",
        enricher=enrich_dataset,
        doc_type="catalog-data",
        filter={"released": True},
        ttl_seconds=86400,
        hostname=hostname,
        catalog_id=catalog_id,
        limit=max_records,
        auto_enrich=True,
    )

    # ------------------------------------------------------------------
    # Prompts
    # ------------------------------------------------------------------
    _prompts.register(ctx, hostname=hostname)
