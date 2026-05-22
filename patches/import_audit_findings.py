"""
import_audit_findings — publish a compliance-audit report from the swarm
into CISO Assistant as a RECORD-type ManagedDocument.

Used in beat 5 → 6 of the wealth-firm demo. After `just demo-audit-after`
in the allium-swarm repo finishes, run this command to publish the report
into the chat's RAG corpus. Sarah can then ask the chat about findings on
the Meridian advisor and have it cite the audit document directly.

The audit output directory (/tmp/allium-swarm-too/audit/ on the host) is
mounted into the backend container at /code/audit-output via
docker-compose.override.yml.

Idempotent. If the report content matches the latest published revision
for the same document, no new revision is created.

Run:
  docker compose exec backend poetry run python manage.py import_audit_findings
  docker compose exec backend poetry run python manage.py import_audit_findings --leg before
  docker compose exec backend poetry run python manage.py import_audit_findings --report /code/audit-output/after/audit-v2.md
"""

from pathlib import Path

from django.core.management.base import BaseCommand


AUDIT_DIR = Path("/code/audit-output")
FOLDER_NAME = "Lorem Ipsum Wealth Partners"


class Command(BaseCommand):
    help = (
        "Publish a swarm compliance-audit report as a RECORD-type ManagedDocument "
        "so the chat can retrieve it."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--leg",
            choices=("before", "after"),
            default="after",
            help="Which audit leg to publish (default: after — the v2-spec run)",
        )
        parser.add_argument(
            "--report",
            help=(
                "Explicit path to the markdown report. Overrides --leg. "
                "Must be a path accessible inside the container (typically "
                "under /code/audit-output)."
            ),
        )

    def handle(self, *args, **options):
        from core.models import Policy
        from doc_management.models import DocumentRevision, ManagedDocument
        from iam.models import Folder

        if options["report"]:
            report_path = Path(options["report"])
            leg_label = "custom"
        else:
            leg = options["leg"]
            label = "v1" if leg == "before" else "v2"
            report_path = AUDIT_DIR / leg / f"audit-{label}.md"
            leg_label = leg

        if not report_path.exists():
            self.stderr.write(
                self.style.ERROR(
                    f"audit report not found: {report_path}\n"
                    "Has the swarm produced output? On the host:\n"
                    "  ls /tmp/allium-swarm-too/audit/"
                )
            )
            return

        content = report_path.read_text(encoding="utf-8")

        folder = Folder.objects.filter(name=FOLDER_NAME).first()
        if folder is None:
            self.stderr.write(
                self.style.ERROR(
                    f"folder '{FOLDER_NAME}' not found. Run setup_demo first."
                )
            )
            return

        # One Policy per audit leg, so the (policy, locale) uniqueness
        # constraint on ManagedDocument is satisfied. The Meridian submission
        # already occupies (policy=None, locale=en); each audit leg gets its
        # own synthetic Policy as its grouping parent.
        leg_to_name = {
            "before": "Compliance Audit — Meridian Estate (v1 spec, baseline)",
            "after": "Compliance Audit — Meridian Estate (v2 spec, post-amendment)",
            "custom": f"Compliance Audit — {report_path.stem}",
        }
        leg_to_description = {
            "before": (
                "Allium-swarm compliance audit of the Meridian estate (advisor, "
                "trade, market-data) against LIWP-POL-AI-001 v1. Baseline before "
                "the FINRA agentic-AI amendment."
            ),
            "after": (
                "Allium-swarm compliance audit of the Meridian estate (advisor, "
                "trade, market-data) against the v2 amended spec. Findings "
                "concentrate on the Meridian AI Scenario Advisor — the agentic "
                "amendments surface gaps the v1 spec did not encode."
            ),
            "custom": f"Allium-swarm compliance audit imported from {report_path}.",
        }
        name = leg_to_name[leg_label]
        description = leg_to_description[leg_label]

        policy, _ = Policy.objects.get_or_create(
            folder=folder,
            name=name,
            defaults={"description": description},
        )

        managed_doc, d_created = ManagedDocument.objects.get_or_create(
            folder=folder,
            name=name,
            policy=policy,
            defaults={
                "document_type": ManagedDocument.DocumentType.RECORD,
                "description": description,
            },
        )
        prefix = self.style.SUCCESS("created") if d_created else "exists "
        self.stdout.write(f"{prefix}  record: {name}")

        latest_any = (
            DocumentRevision.objects.filter(document=managed_doc)
            .order_by("-version_number")
            .first()
        )

        if (
            latest_any
            and latest_any.content.strip() == content.strip()
            and latest_any.status == DocumentRevision.Status.PUBLISHED
        ):
            self.stdout.write(
                f"           revision v{latest_any.version_number} "
                f"(published) unchanged"
            )
            return

        next_version = (latest_any.version_number + 1) if latest_any else 1
        DocumentRevision.objects.create(
            folder=folder,
            document=managed_doc,
            version_number=next_version,
            content=content,
            status=DocumentRevision.Status.PUBLISHED,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"           published revision v{next_version} "
                f"({len(content):,} chars) — indexing queued"
            )
        )
        self.stdout.write(
            "\nThe chat will be able to retrieve this report within ~40s "
            "(once Huey ingest_document completes)."
        )
