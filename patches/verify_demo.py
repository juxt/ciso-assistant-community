"""
verify_demo — post-setup verification for demo-day reliability.

Confirms each load-bearing patch is mounted, loaded and behaving as expected.
Run at the end of sync-demo.sh; non-zero exit on any failure so the script
surfaces problems before demo day.

Checks performed:
  1. Chunker is section-aware (extractors.py patch).
  2. Framework-name detector rejects stopwords (knowledge_graph.py patch).
  3. search_library falls back to vector search when the graph is empty
     (tools.py patch).
  4. IndexedDocument.post_delete handler is registered, so Qdrant chunks
     are cleaned on folder/cascade deletion (signals.py patch).
  5. Chat settings point at LiteLLM via the openai_compatible provider
     with the claude-opus model.
  6. LiteLLM round-trip succeeds against Anthropic with a non-default
     temperature stripped (litellm-config.yaml).

Run:
  docker compose exec backend poetry run python manage.py verify_demo
"""

import io
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verify demo-critical patches and integrations are loaded and working."

    def handle(self, *args, **options):
        passed: list[str] = []
        failed: list[tuple[str, str]] = []

        def check(label: str, body):
            try:
                body()
            except Exception as e:
                failed.append((label, str(e)))
                self.stdout.write(self.style.ERROR(f"FAIL  {label}"))
                self.stdout.write(f"        {e}")
            else:
                passed.append(label)
                self.stdout.write(self.style.SUCCESS(f"PASS  {label}"))

        check("chunker produces section-aware markdown chunks", self._check_chunker)
        check("framework-name detector rejects stopwords", self._check_detector)
        check("search_library falls back to vector search", self._check_vector_fallback)
        check("IndexedDocument.post_delete cleanup handler is registered", self._check_cleanup_signal)
        check("chat settings point at LiteLLM with claude-opus", self._check_chat_settings)
        check("LiteLLM round-trip succeeds with temperature stripped", self._check_litellm_roundtrip)

        self.stdout.write("")
        if failed:
            self.stdout.write(
                self.style.ERROR(
                    f"{len(failed)} of {len(passed) + len(failed)} checks failed."
                )
            )
            sys.exit(1)
        self.stdout.write(self.style.SUCCESS(f"All {len(passed)} checks passed."))

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_chunker(self):
        from chat.extractors import extract_text

        sample = (
            b"# Title\n\n"
            b"intro paragraph\n\n"
            b"## Section A\n\n"
            b"body a\n\n"
            b"## Section B\n\n"
            b"body b\n"
        )
        chunks = extract_text(io.BytesIO(sample))
        if len(chunks) < 2:
            raise AssertionError(f"expected at least 2 section-aware chunks, got {len(chunks)}")
        starts = [c.text.split("\n", 1)[0] for c in chunks]
        if not any("## Section A" in s for s in starts):
            raise AssertionError(
                f"no chunk started with '## Section A'; chunk heads: {starts}"
            )
        if not any("## Section B" in s for s in starts):
            raise AssertionError(
                f"no chunk started with '## Section B'; chunk heads: {starts}"
            )

    def _check_detector(self):
        from chat.tools import _detect_framework_names

        for stop in ("for", "require", "the", "section"):
            if _detect_framework_names(stop) != []:
                raise AssertionError(
                    f"stopword {stop!r} matched a framework; expected []"
                )
        # Legitimate exact ref_id still resolves (sanity check that we didn't over-correct).
        if not _detect_framework_names("DFS-500-2023-11"):
            raise AssertionError(
                "exact ref_id 'DFS-500-2023-11' did not resolve; detector is over-corrected"
            )

    def _check_vector_fallback(self):
        from chat.tools import _dispatch_search_library

        res = _dispatch_search_library(
            {"action": "find_frameworks", "query": "NY DFS Part 500"},
            user_message="What does NY DFS Part 500 require for notice to the superintendent?",
        )
        text = res.get("text", "") if isinstance(res, dict) else ""
        if "Vector search fallback" not in text:
            raise AssertionError(
                "vector fallback did not fire on an empty graph result; "
                f"got text starting: {text[:200]!r}"
            )

    def _check_cleanup_signal(self):
        from django.db.models.signals import post_delete

        from chat.models import IndexedDocument

        receivers = post_delete._live_receivers(IndexedDocument)
        if not receivers:
            raise AssertionError(
                "no post_delete handlers registered on IndexedDocument; "
                "signals.py patch is not loaded or did not connect"
            )

    def _check_chat_settings(self):
        from chat.providers import get_chat_settings

        settings = get_chat_settings()
        provider = settings.get("llm_provider")
        if provider != "openai_compatible":
            raise AssertionError(
                f"llm_provider is {provider!r}; expected 'openai_compatible'. "
                f"Set this in Settings > General in the UI."
            )
        api_base = settings.get("openai_api_base", "")
        if "litellm" not in api_base and "4000" not in api_base:
            raise AssertionError(
                f"openai_api_base is {api_base!r}; expected the LiteLLM endpoint "
                "(http://litellm:4000/v1)"
            )
        model = settings.get("openai_model")
        if model != "claude-opus":
            raise AssertionError(
                f"openai_model is {model!r}; expected 'claude-opus'"
            )

    def _check_litellm_roundtrip(self):
        import httpx

        try:
            resp = httpx.post(
                "http://litellm:4000/v1/chat/completions",
                json={
                    "model": "claude-opus",
                    # Non-default temperature to confirm LiteLLM strips it.
                    "temperature": 0.5,
                    "messages": [
                        {"role": "user", "content": "Reply with the single word OK."}
                    ],
                },
                timeout=30,
            )
        except httpx.HTTPError as e:
            raise AssertionError(f"LiteLLM not reachable at http://litellm:4000: {e}") from e

        if resp.status_code != 200:
            raise AssertionError(
                f"LiteLLM returned HTTP {resp.status_code}: {resp.text[:300]}"
            )
        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as e:
            raise AssertionError(
                f"unexpected LiteLLM response shape: {resp.text[:300]}"
            ) from e
        if not content:
            raise AssertionError("LiteLLM returned empty content")
