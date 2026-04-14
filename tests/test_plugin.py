"""Unit tests for plugin registration."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from facebase_deriva_mcp_plugin.plugin import register


# ---------------------------------------------------------------------------
# Capturing stub for PluginContext
# ---------------------------------------------------------------------------


class _CapturingContext:
    """Minimal PluginContext stub that records all registration calls."""

    def __init__(self) -> None:
        self.env: dict[str, str] = {}
        self.web_sources: list[dict] = []
        self.dataset_indexers: list[dict] = []
        self.prompts: dict[str, Any] = {}
        self.tools: dict[str, Any] = {}

    def rag_web_source(self, name: str, base_url: str, **kwargs: Any) -> None:
        self.web_sources.append({"name": name, "base_url": base_url, **kwargs})

    def rag_dataset_indexer(self, schema: str, table: str, enricher: Any, **kwargs: Any) -> None:
        self.dataset_indexers.append({"schema": schema, "table": table, "enricher": enricher, **kwargs})

    def tool(self, *args: Any, mutates: Any = None, **kwargs: Any):
        return lambda fn: fn

    def resource(self, uri: str, *args: Any, **kwargs: Any):
        return lambda fn: fn

    def prompt(self, name: str = "", *args: Any, **kwargs: Any):
        def decorator(fn: Any) -> Any:
            self.prompts[name] = fn
            return fn
        return decorator


@pytest.fixture()
def ctx() -> _CapturingContext:
    return _CapturingContext()


@pytest.fixture()
def staging_ctx() -> _CapturingContext:
    c = _CapturingContext()
    c.env = {"FACEBASE_DERIVA_MCP_PLUGIN_HOSTNAME": "dev.facebase.org", "FACEBASE_DERIVA_MCP_PLUGIN_MAX_INDEXED_WEB_PAGES": "10"}
    return c


# ---------------------------------------------------------------------------
# RAG source registration
# ---------------------------------------------------------------------------


def test_register_declares_web_source(ctx):
    register(ctx)
    assert len(ctx.web_sources) == 1
    src = ctx.web_sources[0]
    assert src["name"] == "facebase-web"
    assert src["base_url"] == "https://www.facebase.org"


def test_register_declares_dataset_indexer(ctx):
    register(ctx)
    assert len(ctx.dataset_indexers) == 1
    idx = ctx.dataset_indexers[0]
    assert idx["schema"] == "isa"
    assert idx["table"] == "dataset"
    assert callable(idx["enricher"])


def test_dataset_indexer_filter_released(ctx):
    register(ctx)
    idx = ctx.dataset_indexers[0]
    assert idx.get("filter", {}).get("released") is True


def test_dataset_indexer_has_ttl(ctx):
    register(ctx)
    idx = ctx.dataset_indexers[0]
    assert idx.get("ttl_seconds", 0) > 0


def test_dataset_indexer_enricher_is_enrich_dataset(ctx):
    from facebase_deriva_mcp_plugin.enricher import enrich_dataset
    register(ctx)
    idx = ctx.dataset_indexers[0]
    assert idx["enricher"] is enrich_dataset


def test_dataset_indexer_auto_enrich_enabled(ctx):
    register(ctx)
    idx = ctx.dataset_indexers[0]
    assert idx.get("auto_enrich") is True


# ---------------------------------------------------------------------------
# Prompt registration
# ---------------------------------------------------------------------------


def test_register_declares_facebase_assistant_prompt(ctx):
    register(ctx)
    assert "facebase-assistant" in ctx.prompts


def test_register_declares_find_datasets_prompt(ctx):
    register(ctx)
    assert "find-datasets" in ctx.prompts


def test_register_declares_explore_anatomy_prompt(ctx):
    register(ctx)
    assert "explore-anatomy" in ctx.prompts


def test_facebase_assistant_prompt_mentions_hostname(ctx):
    register(ctx)
    result = ctx.prompts["facebase-assistant"](hostname="test.facebase.org")
    assert "test.facebase.org" in result


def test_find_datasets_prompt_includes_topic(ctx):
    register(ctx)
    result = ctx.prompts["find-datasets"](topic="cleft palate mouse models")
    assert "cleft palate mouse models" in result


def test_explore_anatomy_prompt_includes_term(ctx):
    register(ctx)
    result = ctx.prompts["explore-anatomy"](anatomy_term="palate")
    assert "palate" in result


# ---------------------------------------------------------------------------
# Hostname / env configuration
# ---------------------------------------------------------------------------


def test_web_source_uses_default_hostname(ctx):
    register(ctx)
    assert ctx.web_sources[0]["base_url"] == "https://www.facebase.org"


def test_web_source_uses_env_hostname(staging_ctx):
    register(staging_ctx)
    assert staging_ctx.web_sources[0]["base_url"] == "https://dev.facebase.org"


def test_web_source_uses_env_max_pages(staging_ctx):
    register(staging_ctx)
    assert staging_ctx.web_sources[0]["max_pages"] == 10


def test_assistant_prompt_default_hostname_in_output(ctx):
    register(ctx)
    result = ctx.prompts["facebase-assistant"]()
    assert "www.facebase.org" in result


def test_assistant_prompt_staging_hostname_in_output(staging_ctx):
    register(staging_ctx)
    result = staging_ctx.prompts["facebase-assistant"]()
    assert "dev.facebase.org" in result
