#!/usr/bin/env python3
"""
Run the foil test against a running CISO Assistant stack.

Pretends to be Sarah, the AI Governance Director reviewing the
RolloverAssist submission. Opens a fresh chat session, pastes the
submission as the opening message, then asks five follow-up questions.
Captures the full transcript to demo-content/foil-runs/{timestamp}.md
so you can re-read what Claude actually said.

The chat has the LIWP AI Governance Policy and the FINOS AIR subset
indexed via the document RAG path; this is the *foil* — Claude works
from natural-language policy prose, with no Allium spec.

Usage:
  python3 demo-content/run_foil.py
  python3 demo-content/run_foil.py --base https://localhost:8443

Reads credentials from the repo-root .env. Output is a markdown file
in demo-content/foil-runs/. Run it 2-3 times to see what's consistent
vs flaky across runs.
"""

import argparse
import json
import os
import re
import ssl
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"
SUBMISSION_FILE = REPO_ROOT / "demo-content" / "rolloverassist-submission.md"
OUTPUT_DIR = REPO_ROOT / "demo-content" / "foil-runs"

FOLDER_NAME = "Lorem Ipsum Wealth Partners"

SARAH_PROMPTS = [
    # 1 — opener with the submission paste
    None,  # placeholder, computed from SUBMISSION_FILE
    # 2 — tier
    "Help me work through this. Read me your view on the tier.",
    # 3 — High-tier control gaps
    "Walk me through what High requires that isn't in the submission.",
    # 4 — HITL
    "Their HITL claim says 'advisor reviews each draft'. What does the policy actually require of HITL?",
    # 5 — Reg BI
    "Reg BI exposure. Has anyone mapped this submission against the firm's rollover obligations?",
    # 6 — Precedent
    "Have we approved comparable AI deployments before? What were the conditions?",
]


def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _http(method: str, url: str, *, token: str | None = None, body: dict | None = None,
          stream: bool = False, timeout: float = 240.0):
    """urllib wrapper that returns either parsed JSON (non-stream) or the raw response (stream)."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Token {token}"
    data = json.dumps(body or {}).encode("utf-8") if body is not None else None
    req = urlrequest.Request(url, data=data, headers=headers, method=method)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # self-signed Caddy cert
    resp = urlrequest.urlopen(req, timeout=timeout, context=ctx)
    if stream:
        return resp
    return json.loads(resp.read().decode("utf-8"))


def authenticate(base: str, env: dict) -> str:
    user = env.get("DJANGO_SUPERUSER_EMAIL")
    pwd = env.get("DJANGO_SUPERUSER_PASSWORD")
    if not user or not pwd:
        sys.exit("DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_PASSWORD missing from .env")
    payload = _http("POST", f"{base}/api/iam/login/", body={"username": user, "password": pwd})
    return payload["token"]


def find_folder_id(base: str, token: str, folder_name: str) -> str:
    payload = _http("GET", f"{base}/api/folders/", token=token)
    items = payload if isinstance(payload, list) else payload.get("results", [])
    for item in items:
        if item.get("name") == folder_name:
            return item["id"]
    sys.exit(f"Folder '{folder_name}' not found. Run ./sync-demo.sh first.")


def create_session(base: str, token: str, folder_id: str) -> str:
    payload = _http("POST", f"{base}/api/chat/sessions/", token=token,
                    body={"folder": folder_id, "title": "Foil run — RolloverAssist review"})
    return payload["id"]


def send_message_streaming(base: str, token: str, session_id: str, content: str) -> tuple[str, str]:
    """Send a message, consume the SSE stream, return (assistant_content, thinking_content)."""
    url = f"{base}/api/chat/sessions/{session_id}/message/"
    resp = _http("POST", url, token=token, body={"content": content}, stream=True, timeout=240.0)

    assistant_chunks: list[str] = []
    thinking_chunks: list[str] = []
    buffer = b""
    for raw in resp:
        buffer += raw
        while b"\n\n" in buffer:
            event_block, buffer = buffer.split(b"\n\n", 1)
            for line in event_block.decode("utf-8", errors="replace").splitlines():
                if not line.startswith("data:"):
                    continue
                payload_str = line[5:].lstrip()
                try:
                    event = json.loads(payload_str)
                except json.JSONDecodeError:
                    continue
                ev_type = event.get("type")
                if ev_type == "token":
                    assistant_chunks.append(event.get("content", ""))
                elif ev_type == "thinking":
                    thinking_chunks.append(event.get("content", ""))
                elif ev_type == "done":
                    return "".join(assistant_chunks), "".join(thinking_chunks)
                elif ev_type == "error":
                    return f"[ERROR] {event.get('content','unknown')}", "".join(thinking_chunks)
    return "".join(assistant_chunks), "".join(thinking_chunks)


def write_transcript(base: str, prompts: list[str], responses: list[tuple[str, str]]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    outpath = OUTPUT_DIR / f"foil-run_{ts}.md"
    lines = [
        f"# Foil run — {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"Target: `{base}`",
        f"Persona: Sarah Chen, Director of AI Governance, Lorem Ipsum Wealth Partners",
        f"Scenario: reviewing the RolloverAssist deployment submission, no Allium spec in the loop.",
        "",
    ]
    for i, (prompt, (assistant, thinking)) in enumerate(zip(prompts, responses), 1):
        lines.append(f"## Exchange {i}")
        lines.append("")
        lines.append("### Sarah")
        lines.append("")
        lines.append(prompt.strip())
        lines.append("")
        lines.append("### Copilot")
        lines.append("")
        lines.append(assistant.strip() or "_(no content)_")
        lines.append("")
        if thinking.strip():
            lines.append("<details><summary>thinking</summary>")
            lines.append("")
            lines.append(thinking.strip())
            lines.append("")
            lines.append("</details>")
            lines.append("")
        lines.append("---")
        lines.append("")
    outpath.write_text("\n".join(lines), encoding="utf-8")
    return outpath


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="https://localhost:8443",
                        help="Base URL of the CISO Assistant API (default: %(default)s)")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    if not ENV_FILE.exists():
        sys.exit(f"Missing {ENV_FILE}")
    env = load_env(ENV_FILE)

    if not SUBMISSION_FILE.exists():
        sys.exit(f"Missing submission file: {SUBMISSION_FILE}")
    submission_text = SUBMISSION_FILE.read_text(encoding="utf-8")

    prompts = SARAH_PROMPTS.copy()
    prompts[0] = (
        "I'm reviewing an AI deployment submission from the Wealth Management business "
        "team. Help me work through it. Here is the submission in full:\n\n"
        "---\n\n"
        f"{submission_text}\n\n"
        "---\n\n"
        "Once you've read it, wait for my first question."
    )

    print(f"==> authenticating against {base}")
    try:
        token = authenticate(base, env)
    except (HTTPError, URLError) as e:
        sys.exit(f"auth failed: {e}")
    print(f"    ok ({len(token)}-char token)")

    print(f"==> finding folder '{FOLDER_NAME}'")
    folder_id = find_folder_id(base, token, FOLDER_NAME)
    print(f"    {folder_id}")

    print("==> creating chat session")
    session_id = create_session(base, token, folder_id)
    print(f"    {session_id}")

    responses: list[tuple[str, str]] = []
    for i, prompt in enumerate(prompts, 1):
        snippet = re.sub(r"\s+", " ", prompt)[:80]
        print(f"==> exchange {i}/{len(prompts)}: {snippet!r}")
        t0 = time.time()
        try:
            assistant, thinking = send_message_streaming(base, token, session_id, prompt)
        except (HTTPError, URLError) as e:
            print(f"    request failed: {e}")
            responses.append((f"[ERROR] {e}", ""))
            continue
        dt = time.time() - t0
        print(f"    {len(assistant):,} chars assistant, {len(thinking):,} chars thinking, {dt:.1f}s")
        responses.append((assistant, thinking))

    outpath = write_transcript(base, prompts, responses)
    print(f"\n==> transcript written to {outpath}")


if __name__ == "__main__":
    main()
