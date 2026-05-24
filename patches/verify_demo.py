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


class _TransientUpstream(Exception):
    """Raised when a check fails due to a transient upstream condition
    (e.g. Anthropic overloaded_error) rather than an infrastructure problem."""


class Command(BaseCommand):
    help = "Verify demo-critical patches and integrations are loaded and working."

    def handle(self, *args, **options):
        passed: list[str] = []
        failed: list[tuple[str, str]] = []
        warned: list[tuple[str, str]] = []

        def check(label: str, body):
            try:
                body()
            except _TransientUpstream as e:
                warned.append((label, str(e)))
                self.stdout.write(self.style.WARNING(f"WARN  {label}"))
                self.stdout.write(f"        {e}")
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
        check("fallback surfaces firm policy, not just library", self._check_fallback_reaches_firm_policy)
        check("IndexedDocument.post_delete cleanup handler is registered", self._check_cleanup_signal)
        check("both demo policies are indexed in Qdrant", self._check_demo_policies_indexed)
        import os
        use_mock = os.environ.get("MOCK_LLM", "").lower() in ("1", "true", "yes")
        if use_mock:
            check("chat settings point at mock-llm with claude-sonnet", self._check_chat_settings_mock)
            check("mock-llm reachable and serving", self._check_mock_llm_reachable)
        else:
            check("chat settings point at LiteLLM with claude-sonnet", self._check_chat_settings)
            check("LiteLLM round-trip succeeds with temperature stripped", self._check_litellm_roundtrip)

        total = len(passed) + len(failed) + len(warned)
        self.stdout.write("")
        if failed:
            self.stdout.write(
                self.style.ERROR(f"{len(failed)} of {total} checks failed.")
            )
            sys.exit(1)
        if warned:
            self.stdout.write(
                self.style.WARNING(
                    f"{len(passed)} passed, {len(warned)} warned (transient upstream)."
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "Re-run `manage.py verify_demo` in a few minutes to confirm."
                )
            )
            return
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

    def _check_fallback_reaches_firm_policy(self):
        """Confirm the search_library fallback returns firm-policy chunks,
        not just community library content. Catches regressions where the
        fallback gets crowded out by the ~65k library chunks."""
        from chat.tools import _dispatch_search_library

        res = _dispatch_search_library(
            {"action": "find_frameworks", "query": "NY DFS Part 500"},
            user_message=(
                "Walk me through what High tier requires that is not in "
                "the submission"
            ),
        )
        text = res.get("text", "") if isinstance(res, dict) else ""
        if "policy-AI Governance Policy" not in text:
            raise AssertionError(
                "fallback did not surface 'policy-AI Governance Policy' "
                "chunks — firm policy is being crowded out by library "
                "content. Got text starting: " + repr(text[:300])
            )

    def _check_demo_policies_indexed(self):
        """Confirm both demo policies have document chunks in Qdrant."""
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            MatchValue,
        )

        from chat.rag import COLLECTION_NAME, get_qdrant_client

        # Match on filename prefix so the check survives revision bumps
        # (setup_demo creates rev2 when policy content changes).
        expected_prefixes = {
            "policy-AI Governance Policy-rev",
            "policy-FINOS AI Readiness Governance Framework (adopted)-rev",
        }
        client = get_qdrant_client()
        # Scroll all document chunks once, then check prefixes locally.
        seen_prefixes = set()
        next_offset = None
        while True:
            points, next_offset = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="source_type",
                            match=MatchValue(value="document"),
                        ),
                    ]
                ),
                limit=200,
                offset=next_offset,
                with_payload=["filename"],
            )
            for p in points:
                fn = (p.payload or {}).get("filename", "")
                for prefix in expected_prefixes:
                    if fn.startswith(prefix):
                        seen_prefixes.add(prefix)
            if next_offset is None:
                break
        missing = expected_prefixes - seen_prefixes
        if missing:
            raise AssertionError(
                "demo policy chunks missing from Qdrant: "
                + ", ".join(sorted(missing))
                + ". Run `manage.py setup_demo` and wait for indexing."
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
                "setup_demo configures this automatically; re-run it."
            )
        api_base = settings.get("openai_api_base", "")
        if "litellm" not in api_base and "4000" not in api_base:
            raise AssertionError(
                f"openai_api_base is {api_base!r}; expected the LiteLLM endpoint "
                "(http://litellm:4000/v1)"
            )
        model = settings.get("openai_model")
        if model != "claude-sonnet":
            raise AssertionError(
                f"openai_model is {model!r}; expected 'claude-sonnet'"
            )

    def _check_chat_settings_mock(self):
        from chat.providers import get_chat_settings

        settings = get_chat_settings()
        provider = settings.get("llm_provider")
        if provider != "openai_compatible":
            raise AssertionError(
                f"llm_provider is {provider!r}; expected 'openai_compatible'."
            )
        api_base = settings.get("openai_api_base", "")
        if "mock-llm" not in api_base or "4001" not in api_base:
            raise AssertionError(
                f"openai_api_base is {api_base!r}; expected the mock-llm endpoint "
                "(http://mock-llm:4001/v1). Re-run setup_demo with MOCK_LLM=1."
            )
        model = settings.get("openai_model")
        if model != "claude-sonnet":
            raise AssertionError(
                f"openai_model is {model!r}; expected 'claude-sonnet'"
            )

    def _check_mock_llm_reachable(self):
        import httpx

        try:
            resp = httpx.get("http://mock-llm:4001/healthz", timeout=5)
        except httpx.ConnectError as e:
            raise AssertionError(
                f"mock-llm not reachable at http://mock-llm:4001 — is the container up? "
                f"(cd mock-llm && docker compose up -d). Underlying error: {e}"
            ) from e
        if resp.status_code != 200:
            raise AssertionError(
                f"mock-llm /healthz returned {resp.status_code}: {resp.text[:200]}"
            )
        try:
            data = resp.json()
        except ValueError as e:
            raise AssertionError(
                f"mock-llm /healthz returned non-JSON: {resp.text[:200]}"
            ) from e
        if data.get("status") != "ok":
            raise AssertionError(f"mock-llm /healthz status not ok: {data!r}")
        if (data.get("beats") or 0) < 1:
            raise AssertionError(
                "mock-llm reports zero beats loaded — responses.yaml empty or unparseable?"
            )

    def _check_litellm_roundtrip(self):
        import time

        import httpx

        # Anthropic returns transient overloaded_error in waves; LiteLLM retries
        # twice internally, which can stretch a single attempt past 30s. Give
        # the check enough headroom and retry once at our level.
        attempts = 2
        last_error: str | None = None
        for attempt in range(1, attempts + 1):
            try:
                resp = httpx.post(
                    "http://litellm:4000/v1/chat/completions",
                    json={
                        "model": "claude-sonnet",
                        "temperature": 0.5,  # confirms LiteLLM strips it
                        "messages": [
                            {"role": "user", "content": "Reply with the single word OK."}
                        ],
                    },
                    timeout=90,
                )
            except httpx.ConnectError as e:
                raise AssertionError(
                    f"LiteLLM not reachable at http://litellm:4000 (infra problem): {e}"
                ) from e
            except httpx.HTTPError as e:
                last_error = str(e)
                if attempt < attempts:
                    time.sleep(5)
                    continue
                raise AssertionError(
                    f"LiteLLM call failed after {attempts} attempts: {last_error}"
                )

            if resp.status_code == 200:
                try:
                    content = resp.json()["choices"][0]["message"]["content"]
                except (KeyError, IndexError, ValueError) as e:
                    raise AssertionError(
                        f"unexpected LiteLLM response shape: {resp.text[:300]}"
                    ) from e
                if not content:
                    raise AssertionError("LiteLLM returned empty content")
                return  # success

            # Distinguish transient upstream overload (Anthropic) from real failures.
            body_lower = resp.text.lower()
            if (
                "overloaded" in body_lower
                or "rate_limit" in body_lower
                or "rate limit" in body_lower
            ):
                if attempt < attempts:
                    time.sleep(5)
                    continue
                raise _TransientUpstream(
                    "Anthropic overloaded after retry. LiteLLM proxy is fine; "
                    "this is a transient API condition. Re-run in a few minutes."
                )

            if resp.status_code >= 500 and attempt < attempts:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                time.sleep(5)
                continue
            raise AssertionError(
                f"LiteLLM returned HTTP {resp.status_code}: {resp.text[:300]}"
            )
