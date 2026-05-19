"""
enable_allium — switch the demo chat into Allium-grounded mode.

Two coordinated state changes:

  1. Set the chat_system_prompt GlobalSetting to the Allium skill primer
     (read from /code/demo-content/allium-skill-primer.md). The primer
     gives the model behavioural instructions for working with Allium
     specs and points at the constructs it should consult.

  2. Promote the latest DocumentRevision of the firm's Allium spec
     ManagedDocument to Published. The signal patch picks this up and
     indexes its chunks into Qdrant; retrieval can then reach them.

The reverse command is disable_allium.

Run:
  docker compose exec backend poetry run python manage.py enable_allium
"""

from pathlib import Path

from django.core.management.base import BaseCommand


PRIMER_PATH = Path("/code/demo-content/allium-skill-primer.md")
SPEC_POLICY_NAME = "AI Governance Policy — Executable Specification"


class Command(BaseCommand):
    help = "Switch the chat into Allium-grounded mode (system prompt + publish spec)."

    def handle(self, *args, **options):
        from core.models import Policy
        from doc_management.models import DocumentRevision, ManagedDocument
        from global_settings.models import GlobalSettings

        # --- Step 1: load the primer and set chat_system_prompt ---
        if not PRIMER_PATH.exists():
            self.stderr.write(self.style.ERROR(f"missing primer: {PRIMER_PATH}"))
            return
        primer = PRIMER_PATH.read_text(encoding="utf-8")

        gs, _ = GlobalSettings.objects.get_or_create(name="general", defaults={"value": {}})
        current = gs.value or {}
        if current.get("chat_system_prompt") == primer:
            self.stdout.write("chat_system_prompt already set to Allium primer")
        else:
            current["chat_system_prompt"] = primer
            gs.value = current
            gs.save(update_fields=["value"])
            self.stdout.write(self.style.SUCCESS(
                f"chat_system_prompt set to Allium primer ({len(primer):,} chars)"
            ))

        # --- Step 2: publish the spec's latest revision ---
        policy = Policy.objects.filter(name=SPEC_POLICY_NAME).first()
        if not policy:
            self.stderr.write(self.style.ERROR(
                f"policy not found: '{SPEC_POLICY_NAME}'. "
                "Run setup_demo to create it."
            ))
            return
        managed_doc = ManagedDocument.objects.filter(policy=policy).first()
        if not managed_doc:
            self.stderr.write(self.style.ERROR(
                f"managed document missing for policy '{SPEC_POLICY_NAME}'"
            ))
            return
        revision = (
            DocumentRevision.objects.filter(document=managed_doc)
            .order_by("-version_number")
            .first()
        )
        if not revision:
            self.stderr.write(self.style.ERROR(
                f"no revision exists for '{SPEC_POLICY_NAME}'"
            ))
            return

        if revision.status == DocumentRevision.Status.PUBLISHED:
            self.stdout.write(f"spec revision v{revision.version_number} already PUBLISHED")
        else:
            revision.status = DocumentRevision.Status.PUBLISHED
            revision.save(update_fields=["status"])
            self.stdout.write(self.style.SUCCESS(
                f"spec revision v{revision.version_number} -> PUBLISHED "
                "(Huey will index it shortly)"
            ))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Allium mode ENABLED."))
        self.stdout.write(
            "Open a fresh chat session in CISO Assistant to see the change. "
            "Indexing of the spec takes ~40s on first publish."
        )
