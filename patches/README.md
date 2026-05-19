# Chat module patches

Two small fixes mounted over the upstream backend image via `docker-compose.override.yml`. Both target bugs that surfaced when using natural-language framework queries in the chat. Both are generic improvements, not demo-specific.

## `knowledge_graph.py`

`_resolve_framework` matched single common English words against framework names — "for" against `CROE-for-FMI`, "require" against `NIS 2 directive requirements` — at exactly the 0.25 score threshold (which used a strict `<` comparison and so let 0.25 through). With two spurious matches, `_detect_framework_names` returned two URNs, and `_dispatch_search_library`'s `auto_upgrade_to_compare` then forced a `compare_frameworks` action on the wrong frameworks.

Fix: add a single-token stopword filter and raise the threshold to 0.5. Multi-token phrases and exact ref_id matches are unaffected.

## `tools.py`

`_dispatch_search_library` only used the knowledge graph, which matches by case-insensitive substring on framework names and ref_ids. A user question like "NY DFS Part 500" doesn't substring-match "NY DFS 500 with 2023-11 amendments", so the tool returned no results. Worse, `views.py` *replaces* the default Qdrant vector context with the tool's result when the LLM picks this tool, so the LLM never sees what Qdrant could have surfaced.

Fix: when the graph search returns nothing, fall back to a vector search over the `library` partition and return those hits.

## Upstreaming

Both patches are candidates for an upstream PR. If you do that, drop this overlay arrangement from `docker-compose.override.yml` once the fix lands in a tagged backend image.
