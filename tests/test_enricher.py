"""Unit tests for the FaceBase dataset enricher."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from facebase_deriva_mcp_plugin.enricher import enrich_dataset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_catalog(responses: dict[str, list[dict]]) -> MagicMock:
    """Return a mock catalog whose .get(path).json() returns fixture data.

    responses maps URL substrings to the list of dicts to return. The first
    matching key wins (checked in insertion order).
    """
    catalog = MagicMock()

    def _get(path: str) -> MagicMock:
        for key, data in responses.items():
            if key in path:
                resp = MagicMock()
                resp.json.return_value = data
                return resp
        resp = MagicMock()
        resp.json.return_value = []
        return resp

    catalog.get.side_effect = _get
    return catalog


_BASE_ROW = {
    "RID": "ABC-1234",
    "accession": "FB00000001",
    "DOI": "10.1234/fb.001",
    "title": "Test Craniofacial Dataset",
    "description": "A dataset about craniofacial development.",
    "study_design": "Genomic sequencing of mouse craniofacial tissue.",
    "released": True,
}


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------


async def test_enricher_returns_string():
    catalog = _make_catalog({})
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert isinstance(result, str)


async def test_enricher_includes_rid():
    catalog = _make_catalog({})
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert "ABC-1234" in result


async def test_enricher_includes_accession():
    catalog = _make_catalog({})
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert "FB00000001" in result


async def test_enricher_includes_doi():
    catalog = _make_catalog({})
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert "10.1234/fb.001" in result


async def test_enricher_includes_title():
    catalog = _make_catalog({})
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert "Test Craniofacial Dataset" in result


async def test_enricher_includes_description():
    catalog = _make_catalog({})
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert "craniofacial development" in result


async def test_enricher_includes_study_design():
    catalog = _make_catalog({})
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert "Genomic sequencing" in result


# ---------------------------------------------------------------------------
# Project / consortium / contributors
# ---------------------------------------------------------------------------


async def test_enricher_includes_project_name():
    catalog = _make_catalog({
        "isa:project/name": [{"name": "Craniofacial Atlas Project"}],
    })
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert "Craniofacial Atlas Project" in result


async def test_enricher_includes_consortium_name():
    catalog = _make_catalog({
        "vocab:consortium": [{"name": "FaceBase Consortium"}],
    })
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert "FaceBase Consortium" in result


async def test_enricher_includes_contributors():
    catalog = _make_catalog({
        "dataset_contributor": [
            {"name": "Jane Smith"},
            {"name": "John Doe"},
        ],
    })
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert "Jane Smith" in result
    assert "John Doe" in result


# ---------------------------------------------------------------------------
# Controlled vocabulary terms
# ---------------------------------------------------------------------------


async def test_enricher_includes_species():
    catalog = _make_catalog({
        "dataset_species": [{"name": "Mus musculus", "synonyms": ["mouse"]}],
    })
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert "Mus musculus" in result
    assert "mouse" in result


async def test_enricher_includes_anatomy():
    catalog = _make_catalog({
        "dataset_anatomy": [{"name": "palate", "synonyms": ["palatine"]}],
    })
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert "palate" in result
    assert "palatine" in result


async def test_enricher_includes_phenotype():
    catalog = _make_catalog({
        "dataset_phenotype": [{"name": "cleft palate", "synonyms": []}],
    })
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert "cleft palate" in result


async def test_enricher_omits_empty_vocab_section():
    """Vocabulary sections with no terms must not appear in output."""
    catalog = _make_catalog({})
    result = await enrich_dataset(_BASE_ROW, catalog)
    # No gene data was provided -- the Gene section should be absent
    assert "## Gene" not in result


async def test_enricher_includes_synonyms_joined():
    """Multiple synonyms are joined with commas after the primary name."""
    catalog = _make_catalog({
        "dataset_syndrome": [{"name": "Treacher Collins syndrome", "synonyms": ["TCS", "mandibulofacial dysostosis"]}],
    })
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert "Treacher Collins syndrome, TCS, mandibulofacial dysostosis" in result


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


async def test_enricher_handles_none_description():
    row = {**_BASE_ROW, "description": None}
    catalog = _make_catalog({})
    result = await enrich_dataset(row, catalog)
    assert "ABC-1234" in result  # still returns valid output


async def test_enricher_handles_none_study_design():
    row = {**_BASE_ROW, "study_design": None}
    catalog = _make_catalog({})
    result = await enrich_dataset(row, catalog)
    assert "Not available" in result


async def test_enricher_handles_missing_doi():
    row = {**_BASE_ROW, "DOI": None}
    catalog = _make_catalog({})
    result = await enrich_dataset(row, catalog)
    assert "N/A" in result


async def test_enricher_rid_is_url_encoded_in_catalog_calls():
    """RID values with special characters must be percent-encoded in paths."""
    row = {**_BASE_ROW, "RID": "A/B:C"}
    catalog = _make_catalog({})
    await enrich_dataset(row, catalog)
    # All get() calls must have the RID encoded, not literal slashes/colons
    for call in catalog.get.call_args_list:
        path = call.args[0]
        assert "A/B:C" not in path, f"Unencoded RID found in path: {path}"


# ---------------------------------------------------------------------------
# Fetch failure resilience
# ---------------------------------------------------------------------------


async def test_enricher_continues_if_project_fetch_fails():
    """A failed project fetch must not abort enrichment -- returns partial output."""
    catalog = MagicMock()
    catalog.get.side_effect = OSError("network error")
    result = await enrich_dataset(_BASE_ROW, catalog)
    # Still returns valid Markdown with the base row fields
    assert "ABC-1234" in result


async def test_enricher_continues_if_vocab_fetch_fails():
    """A failed vocab fetch for one term must not abort enrichment."""
    def _get(path):
        if "dataset_species" in path:
            raise OSError("timeout")
        resp = MagicMock()
        resp.json.return_value = []
        return resp

    catalog = MagicMock()
    catalog.get.side_effect = _get
    result = await enrich_dataset(_BASE_ROW, catalog)
    assert "ABC-1234" in result
    assert "## Species" not in result  # failed fetch -- section absent