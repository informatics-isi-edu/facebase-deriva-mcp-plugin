# facebase-deriva-mcp-plugin

FaceBase plugin for [deriva-mcp-core](https://github.com/informatics-isi-edu/deriva-mcp-core).

## What it does

When installed alongside `deriva-mcp-core`, this plugin automatically registers:

- **RAG web source** -- crawls `https://www.facebase.org` (up to 300 pages) and indexes content into the vector store.
- **RAG dataset indexer** -- on catalog connect, fetches all released `isa:dataset` rows and enriches each one with project, consortium, contributor, and controlled-vocabulary data (species, gene, anatomy, phenotype, syndrome, genotype, sex, stage, experiment type), then upserts Markdown chunks into the vector store. Re-indexed at most once per hour (TTL-gated).
- **MCP prompts** -- `facebase-assistant`, `find-datasets`, `explore-anatomy`.

## Installation

```bash
pip install facebase-deriva-mcp-plugin
```

The plugin is discovered automatically via the `deriva_mcp.plugins` entry point group. No additional configuration is needed beyond enabling RAG in `deriva-mcp-core` (`DERIVA_MCP_RAG_ENABLED=true`).

## Development

`deriva-mcp-core` is not yet published to PyPI. Install it from source first:

```bash
pip install -e ../deriva-mcp-core
pip install -e ".[dev]"
uv run --no-sync pytest
```
