"""
Demo bootstrap as a Django management command.

Creates the firm Folder and two Policies, each with the latest revision
published, from the markdown files in /code/demo-content/. The chat signal
patch indexes published revisions into Qdrant automatically.

Mount this file into the backend (and huey) container at
  /code/chat/management/commands/setup_demo.py
via docker-compose.override.yml so it is discoverable as
`manage.py setup_demo`.

Usage:
  docker compose exec backend poetry run python manage.py setup_demo
  docker compose exec backend poetry run python manage.py setup_demo --reset

Idempotent. Re-running skips a revision if its content matches the latest
published revision. --reset deletes the Folder (and everything under it)
before recreating.
"""

from pathlib import Path

from django.core.management.base import BaseCommand


DEMO_CONTENT_DIR = Path("/code/demo-content")
FOLDER_NAME = "Lorem Ipsum Wealth Partners"

POLICIES = [
    {
        "name": "FINOS AI Readiness Governance Framework (adopted)",
        "file": "finos-air-governance-subset.md",
        "description": (
            "Foundational AI risk catalogue maintained by the Fintech Open Source "
            "Foundation, adopted as the firm's baseline. CC BY 4.0."
        ),
        # Initial DocumentRevision status. "published" makes it retrievable
        # by the chat immediately. "draft" creates the document but holds
        # back indexing; useful for the Allium spec which the demo toggles
        # in and out via enable_allium/disable_allium.
        "initial_status": "published",
    },
    {
        "name": "AI Governance Policy",
        "file": "lorem-ipsum-wealth-partners-ai-governance-policy-v1-prose.md",
        "description": (
            "The firm's operationalisation of the FINOS AIR Governance Framework. "
            "Defines roles, tier criteria, controls per tier, and domain obligations."
        ),
        "initial_status": "published",
    },
    {
        "name": "AI Governance Policy — Executable Specification",
        "file": "liwp-ai-governance.allium",
        "description": (
            "The firm's AI Governance Policy expressed in Allium — the executable "
            "form of LIWP-POL-AI-001. Indexed only when Allium mode is enabled."
        ),
        # The demo starts in foil mode. enable_allium promotes this to Published.
        "initial_status": "draft",
    },
]


class Command(BaseCommand):
    help = (
        "Bootstrap the wealth-firm demo: Folder + two Policies with published "
        "DocumentRevisions sourced from /code/demo-content/"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the demo Folder and all contents before recreating",
        )

    def handle(self, *args, **options):
        from iam.models import Folder

        reset = options["reset"]

        if reset:
            qs = Folder.objects.filter(name=FOLDER_NAME)
            if qs.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"--reset: deleting folder '{FOLDER_NAME}' and all contents"
                    )
                )
                qs.delete()

        folder, created = Folder.objects.get_or_create(name=FOLDER_NAME)
        prefix = self.style.SUCCESS("created") if created else "exists "
        self.stdout.write(f"{prefix}  folder: {FOLDER_NAME}")

        for spec in POLICIES:
            self._setup_policy(folder, spec)

        self._configure_chat_settings()

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Demo bootstrap complete. Indexing runs asynchronously via Huey; "
                "the first ingest takes ~40s. Watch backend logs for "
                "'auto_queued_document_revision_for_indexing' and Huey logs for "
                "'Indexed document'."
            )
        )

    def _configure_chat_settings(self):
        """
        Wire CISO Assistant's GlobalSettings to point the chat at our LiteLLM
        proxy. Used to be a manual step in the UI; bootstrapping it here means
        a fresh `./sync-demo.sh` lands a fully-configured demo.
        """
        from global_settings.models import GlobalSettings

        target = {
            "llm_provider": "openai_compatible",
            "openai_api_base": "http://litellm:4000/v1",
            "openai_model": "claude-sonnet",
            "openai_api_key": "",
            "embedding_backend": "sentence-transformers",
        }
        gs, _ = GlobalSettings.objects.get_or_create(name="general", defaults={"value": {}})
        current = gs.value or {}
        changed = False
        for k, v in target.items():
            if current.get(k) != v:
                current[k] = v
                changed = True
        if changed:
            gs.value = current
            gs.save(update_fields=["value"])
            self.stdout.write(self.style.SUCCESS("updated chat settings (LLM provider, model, base URL)"))
        else:
            self.stdout.write("chat settings already configured")

    def _setup_policy(self, folder, spec):
        from core.models import Policy
        from doc_management.models import DocumentRevision, ManagedDocument

        name = spec["name"]
        content_path = DEMO_CONTENT_DIR / spec["file"]
        if not content_path.exists():
            self.stderr.write(
                self.style.ERROR(f"missing demo content file: {content_path}")
            )
            return
        content = content_path.read_text(encoding="utf-8")

        policy, p_created = Policy.objects.get_or_create(
            folder=folder,
            name=name,
            defaults={"description": spec.get("description", "")},
        )
        prefix = self.style.SUCCESS("created") if p_created else "exists "
        self.stdout.write(f"{prefix}  policy: {name}")

        managed_doc, d_created = ManagedDocument.objects.get_or_create(
            policy=policy,
            defaults={
                "folder": folder,
                "document_type": ManagedDocument.DocumentType.POLICY,
                "name": name,
            },
        )
        if d_created:
            self.stdout.write("           managed document attached")

        target_status_str = spec.get("initial_status", "published")
        target_status = (
            DocumentRevision.Status.DRAFT
            if target_status_str == "draft"
            else DocumentRevision.Status.PUBLISHED
        )

        latest_any = (
            DocumentRevision.objects.filter(document=managed_doc)
            .order_by("-version_number")
            .first()
        )

        # If a revision already exists with matching content and status, no-op.
        if (
            latest_any
            and latest_any.content.strip() == content.strip()
            and latest_any.status == target_status
        ):
            self.stdout.write(
                f"           revision v{latest_any.version_number} "
                f"({target_status_str}) unchanged"
            )
            return

        next_version = (latest_any.version_number + 1) if latest_any else 1
        DocumentRevision.objects.create(
            folder=folder,
            document=managed_doc,
            version_number=next_version,
            content=content,
            status=target_status,
        )
        if target_status == DocumentRevision.Status.PUBLISHED:
            tail = "indexing queued"
            verb = "published"
        else:
            tail = "not indexed (Draft)"
            verb = "saved as draft"
        self.stdout.write(
            self.style.SUCCESS(
                f"           {verb} revision v{next_version} "
                f"({len(content):,} chars) — {tail}"
            )
        )
