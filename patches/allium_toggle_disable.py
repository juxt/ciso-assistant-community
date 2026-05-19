"""
disable_allium — switch the demo chat back into foil (prose-only) mode.

Reverses enable_allium:

  1. Clears chat_system_prompt, letting CISO Assistant's DEFAULT_SYSTEM_PROMPT
     take over again (the generic GRC assistant behaviour without Allium
     awareness).

  2. Demotes the Allium spec ManagedDocument's latest revision from
     Published to Draft. The signal patch picks this up and retires
     its Qdrant chunks; retrieval can no longer reach them.

Run:
  docker compose exec backend poetry run python manage.py disable_allium
"""

from django.core.management.base import BaseCommand


SPEC_POLICY_NAME = "AI Governance Policy — Executable Specification"


class Command(BaseCommand):
    help = "Switch the chat back into foil (prose-only) mode."

    def handle(self, *args, **options):
        from core.models import Policy
        from doc_management.models import DocumentRevision, ManagedDocument
        from global_settings.models import GlobalSettings

        # --- Step 1: clear chat_system_prompt ---
        gs = GlobalSettings.objects.filter(name="general").first()
        if gs and gs.value and gs.value.get("chat_system_prompt"):
            gs.value["chat_system_prompt"] = ""
            gs.save(update_fields=["value"])
            self.stdout.write(self.style.SUCCESS("chat_system_prompt cleared"))
        else:
            self.stdout.write("chat_system_prompt already empty")

        # --- Step 2: demote spec's published revision to Draft ---
        policy = Policy.objects.filter(name=SPEC_POLICY_NAME).first()
        if not policy:
            self.stdout.write(self.style.WARNING(
                f"policy '{SPEC_POLICY_NAME}' not found; nothing to demote"
            ))
        else:
            managed_doc = ManagedDocument.objects.filter(policy=policy).first()
            if managed_doc:
                published = (
                    DocumentRevision.objects.filter(
                        document=managed_doc,
                        status=DocumentRevision.Status.PUBLISHED,
                    )
                    .order_by("-version_number")
                    .first()
                )
                if published:
                    published.status = DocumentRevision.Status.DRAFT
                    published.save(update_fields=["status"])
                    self.stdout.write(self.style.SUCCESS(
                        f"spec revision v{published.version_number} -> DRAFT "
                        "(Qdrant chunks retired by signal handler)"
                    ))
                else:
                    self.stdout.write("no Published spec revision; nothing to demote")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Allium mode DISABLED — foil active."))
        self.stdout.write(
            "Open a fresh chat session in CISO Assistant to see the change."
        )
