from __future__ import annotations

"""Dataset enricher for FaceBase RAG indexing.

enrich_dataset(row, catalog) is passed to ctx.rag_dataset_indexer() and called
once per released isa:dataset row. It fetches related project, consortium,
contributor, and controlled-vocabulary data via ERMrest attribute paths, then
formats everything as Markdown suitable for chunking and vector indexing.

All catalog HTTP calls use asyncio.to_thread() so the event loop is never
blocked -- the enricher is called once per row during on_catalog_connect and
a large catalog (e.g. 1000+ datasets x 12 fetches each) would otherwise freeze
the server for the entire enrichment window.
"""

import asyncio
import logging
import urllib.parse
from typing import Any

logger = logging.getLogger(__name__)


def _enc(value: Any) -> str:
    return urllib.parse.quote(str(value), safe="")


def _sync_fetch(catalog: Any, path: str) -> list[dict]:
    """Blocking ERMrest GET -- must only be called from inside asyncio.to_thread."""
    return catalog.get(path).json()


async def _fetch(catalog: Any, path: str) -> list[dict]:
    """Non-blocking ERMrest GET. Runs the blocking call in a thread pool."""
    return await asyncio.to_thread(_sync_fetch, catalog, path)


def _md_list(items: list[str]) -> str:
    return "\n".join(f" * {item}" for item in items) if items else "None"


# Vocabulary term tables linked through isa:dataset_{tname} association tables.
_VOCAB_TERMS = (
    "species",
    "gene",
    "experiment_type",
    "anatomy",
    "phenotype",
    "syndrome",
    "genotype",
    "sex",
    "stage",
)


async def enrich_dataset(row: dict, catalog: Any) -> str:
    """Return Markdown describing one FaceBase dataset, enriched with related data.

    Fetches project, consortium, contributors, and nine vocabulary term types
    (each with synonyms) via ERMrest attribute paths. All HTTP calls are wrapped
    in asyncio.to_thread() to avoid blocking the event loop.

    Args:
        row: A single row dict from /entity/isa:dataset (contains RID, title,
            description, study_design, accession, DOI, released, etc.).
        catalog: ERMrest catalog connection (from deriva-py).

    Returns:
        Markdown string ready for chunk_markdown().
    """
    rid_raw = row["RID"]
    rid = _enc(rid_raw)
    logger.debug("Enriching FaceBase dataset %s", rid_raw)

    # Project name
    try:
        project_rows = await _fetch(catalog, f"/attribute/isa:dataset/RID={rid}/isa:project/name")
        project_names = [r["name"] for r in project_rows if r.get("name")]
    except Exception:
        logger.warning("Failed to fetch project for dataset %s", rid_raw, exc_info=True)
        project_names = []

    # Consortium (FK: project -> vocab:consortium)
    try:
        consortium_rows = await _fetch(
            catalog,
            f"/attribute/isa:dataset/RID={rid}/isa:project/vocab:consortium/name:=Name",
        )
        consortium_names = [r["name"] for r in consortium_rows if r.get("name")]
    except Exception:
        logger.warning("Failed to fetch consortium for dataset %s", rid_raw, exc_info=True)
        consortium_names = []

    # Contributors (authors)
    try:
        contributor_rows = await _fetch(
            catalog,
            f"/attribute/isa:dataset/RID={rid}/isa:dataset_contributor/name:=full_name",
        )
        contributor_names = [r["name"] for r in contributor_rows if r.get("name")]
    except Exception:
        logger.warning("Failed to fetch contributors for dataset %s", rid_raw, exc_info=True)
        contributor_names = []

    # Controlled vocabulary terms with synonyms
    vocab: dict[str, list[str]] = {}
    for tname in _VOCAB_TERMS:
        try:
            term_rows = await _fetch(
                catalog,
                f"/attribute/isa:dataset/RID={rid}/isa:dataset_{tname}/vocab:{tname}/name,synonyms",
            )
        except Exception:
            logger.warning(
                "Failed to fetch vocab term %r for dataset %s", tname, rid_raw, exc_info=True
            )
            continue
        terms = []
        for term in term_rows:
            label = term.get("name") or ""
            synonyms = term.get("synonyms") or []
            if label:
                entry = ", ".join([label] + synonyms) if synonyms else label
                terms.append(entry)
        if terms:
            vocab[tname] = terms

    # Build Markdown
    rid_display = row["RID"]
    accession = row.get("accession") or "N/A"
    doi = row.get("DOI") or "N/A"
    title = (row.get("title") or "").strip()
    description = (row.get("description") or "").strip()
    study_design = (row.get("study_design") or "Not available").strip()

    text = f"""# Dataset {rid_display}

{title}

## Dataset Identifiers

 * Record ID (RID): {rid_display}
 * Accession: {accession}
 * DOI: {doi}

## Project

{_md_list(project_names) if project_names else "None"}

## Consortium

{_md_list(consortium_names) if consortium_names else "None"}

## Contributors (Authors)

{_md_list(contributor_names)}

## Description

{description}

## Study Design

{study_design}
"""

    for tname in _VOCAB_TERMS:
        if tname in vocab:
            text += f"""
## {tname.replace("_", " ").title()}

{_md_list(vocab[tname])}
"""

    logger.debug(
        "Enriched dataset %s: project=%s consortium=%s contributors=%d vocab_terms=%s",
        rid_raw,
        project_names[0] if project_names else None,
        consortium_names[0] if consortium_names else None,
        len(contributor_names),
        list(vocab.keys()),
    )
    return text