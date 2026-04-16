from __future__ import annotations

"""MCP prompt registrations for the FaceBase plugin.

Prompts are pre-built conversation starters surfaced by MCP clients. Each
prompt accepts optional arguments and returns a list of messages that prime
the LLM for a specific FaceBase research workflow.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deriva_mcp_core.plugin.api import PluginContext


def register(ctx: PluginContext, hostname: str = "www.facebase.org") -> None:
    """Register FaceBase-specific MCP prompts."""

    @ctx.prompt(name="facebase-assistant")
    def facebase_assistant(hostname: str = hostname, catalog_id: str = "1") -> str:
        return (
            f"You are a FaceBase research assistant with access to the FaceBase data catalog "
            f"at {hostname} (catalog {catalog_id}). FaceBase is the primary data resource for "
            f"craniofacial researchers worldwide, containing datasets on craniofacial development, "
            f"anomalies, and related biological processes.\n\n"
            f"You can help researchers:\n"
            f" * Find datasets by anatomy, phenotype, species, or experimental type\n"
            f" * Explore project and consortium information\n"
            f" * Understand dataset contents, contributors, and study designs\n"
            f" * Navigate controlled vocabulary terms including genes, syndromes, and stages\n\n"
            f"Use the available DERIVA tools to query the catalog and the RAG search tool "
            f"to find semantically relevant datasets. Always include dataset RIDs and accession "
            f"numbers in your responses so researchers can locate records directly."
            
            """ADDITIONAL INSTRUCTIONS:
            1. Answer questions using PRIMARILY the provided FaceBase context, 
                but it is acceptable to fall back on your own knowledge if a question is 
                about a more general, but related topic
            2. For technical/medical terms, provide clear definitions from the context
            3. Organize information logically with proper structure
            4. If the context has partial information, synthesize what's available
            5. Be specific - include dataset DOIs, IDs, RIDs, or specific data when mentioned
            6. If information is insufficient, clearly state what's missing
            7. Cite sources naturally (e.g., "According to dataset FB00001234...")
    
            CONTEXT USAGE:
            - Prioritize sources with higher relevance scores
            - Cross-reference multiple sources when they discuss the same topic
            - Extract specific facts: anatomical terms, genes, species, methods
            - Include relevant technical details and identifiers
            """
        )

    @ctx.prompt(name="find-datasets")
    def find_datasets(
        topic: str,
        hostname: str = "www.facebase.org",
        catalog_id: str = "1",
    ) -> str:
        return (
            f"Search the FaceBase catalog at {hostname} (catalog {catalog_id}) for datasets "
            f"related to: {topic}\n\n"
            f"Steps to follow:\n"
            f"1. Use rag_search to find semantically relevant datasets matching the topic.\n"
            f"2. Use get_entities or query_attribute on isa:dataset to retrieve structured "
            f"   metadata for the most promising candidates.\n"
            f"3. For each relevant dataset, report: RID, accession, title, description summary, "
            f"   project, consortium, species, anatomy, phenotype, and experiment type.\n"
            f"4. STOP: IMPORTANT: If the topic names a specific anatomy term, gene, syndrome, or phenotype, "
            f"   also try querying through foreign key relations via query_attribute to the corresponding vocabulary "
            f"   table (e.g. vocab:anatomy, vocab:gene) to find exact controlled-vocabulary matches. "
            f"   Only use regex matching as a fallback.\n\n"
            f"Present results as a ranked list with the most relevant datasets first."
        )

    @ctx.prompt(name="explore-anatomy")
    def explore_anatomy(
        anatomy_term: str,
        hostname: str = "www.facebase.org",
        catalog_id: str = "1",
    ) -> str:
        return (
            f"Explore FaceBase datasets at {hostname} (catalog {catalog_id}) that involve "
            f"the anatomical structure: {anatomy_term}\n\n"
            f"Steps to follow:\n"
            f"1. Query vocab:anatomy to find the canonical term and any synonyms matching "
            f"   '{anatomy_term}'.\n"
            f"2. Use the anatomy RID(s) to traverse isa:dataset_anatomy to find linked datasets.\n"
            f"3. For each dataset found, retrieve: RID, accession, title, species, experiment "
            f"   type, phenotype, syndrome, and project.\n"
            f"4. Summarize the range of experimental approaches and species used to study "
            f"   this anatomical region across all returned datasets.\n\n"
            f"If no exact anatomy match is found, suggest the closest available terms from "
            f"the vocab:anatomy table."
        )