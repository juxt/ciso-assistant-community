"""
Django signals to trigger incremental re-indexing of model objects
when they are created, updated, or deleted.
"""

import structlog

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = structlog.get_logger(__name__)

# Models to index for RAG
INDEXED_MODELS = [
    "core.AppliedControl",
    "core.RiskScenario",
    "core.Asset",
    "core.Threat",
    "core.ComplianceAssessment",
    "core.RiskAssessment",
    "core.RequirementAssessment",
]


def _get_model_classes():
    """Lazily resolve model classes from strings."""
    from django.apps import apps

    classes = []
    for model_path in INDEXED_MODELS:
        app_label, model_name = model_path.split(".")
        try:
            classes.append(apps.get_model(app_label, model_name))
        except LookupError:
            logger.warning("Model %s not found, skipping RAG indexing", model_path)
    return classes


_connected = False


def connect_signals():
    """Connect post_save and post_delete signals for indexed models."""
    global _connected
    if _connected:
        return
    _connected = True

    from django.conf import settings as django_settings

    if not getattr(django_settings, "ENABLE_CHAT", False):
        return

    from global_settings.utils import ff_is_enabled

    for model_class in _get_model_classes():

        @receiver(post_save, sender=model_class, weak=False)
        def on_save(sender, instance, **kwargs):
            if not ff_is_enabled("chat_mode"):
                return
            from django.db import transaction
            from .tasks import index_model_object

            app = sender._meta.app_label
            name = sender.__name__
            obj_id = str(instance.id)
            transaction.on_commit(lambda: index_model_object(app, name, obj_id))

        @receiver(post_delete, sender=model_class, weak=False)
        def on_delete(sender, instance, **kwargs):
            if not ff_is_enabled("chat_mode"):
                return
            from django.db import transaction
            from .tasks import remove_model_object

            app = sender._meta.app_label
            name = sender.__name__
            obj_id = str(instance.id)
            transaction.on_commit(lambda: remove_model_object(app, name, obj_id))

    # Auto-ingest evidence attachments when a new revision is uploaded
    _connect_evidence_signal(ff_is_enabled)

    # Demo patch: auto-ingest managed-document (Policy) revisions and keep the
    # RAG store in sync as revisions are republished, demoted from published,
    # or deleted. Parallels evidence ingestion but with a fuller lifecycle.
    _connect_document_revision_signal(ff_is_enabled)


def _connect_evidence_signal(ff_is_enabled):
    """Connect signal to auto-ingest evidence file attachments."""
    from django.apps import apps

    try:
        EvidenceRevision = apps.get_model("core", "EvidenceRevision")
    except LookupError:
        logger.warning(
            "EvidenceRevision model not found, skipping evidence auto-ingest signal"
        )
        return

    @receiver(post_save, sender=EvidenceRevision, weak=False)
    def on_evidence_revision_save(sender, instance, created, **kwargs):
        if not created or not ff_is_enabled("chat_mode"):
            return
        if not instance.attachment:
            return

        from django.contrib.contenttypes.models import ContentType

        from .models import IndexedDocument
        from .tasks import ingest_document

        # Determine content type from file name
        import mimetypes

        mime_type, _ = mimetypes.guess_type(instance.attachment.name)
        if not mime_type:
            return

        # Only ingest supported file types
        from .extractors import get_extractor

        if not get_extractor(mime_type):
            return

        # Avoid duplicate indexing for same attachment
        ct = ContentType.objects.get_for_model(EvidenceRevision)
        if IndexedDocument.objects.filter(
            source_content_type=ct,
            source_object_id=instance.id,
        ).exists():
            return

        doc = IndexedDocument.objects.create(
            folder=instance.folder,
            file=instance.attachment,
            filename=instance.attachment.name.split("/")[-1],
            content_type=mime_type,
            source_type=IndexedDocument.SourceType.EVIDENCE,
            source_content_type=ct,
            source_object_id=instance.id,
        )
        ingest_document(str(doc.id))
        logger.info("Auto-queued evidence attachment for indexing: %s", doc.filename)


# ---------------------------------------------------------------------------
# Demo patch: ManagedDocument / DocumentRevision auto-ingest with lifecycle.
# ---------------------------------------------------------------------------


def _qdrant_delete_chunks_for_indexed_doc(indexed_document_id):
    """Remove every Qdrant point whose document_id payload matches."""
    from .rag import COLLECTION_NAME, get_qdrant_client
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    try:
        client = get_qdrant_client()
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=str(indexed_document_id)),
                    )
                ]
            ),
        )
    except Exception as e:
        logger.warning(
            "qdrant_chunk_delete_failed",
            indexed_document_id=str(indexed_document_id),
            error=str(e),
        )


def _cleanup_indexed_for_revision(revision_id, revision_content_type):
    """Delete every IndexedDocument tied to a DocumentRevision id, plus chunks."""
    from .models import IndexedDocument

    qs = IndexedDocument.objects.filter(
        source_content_type=revision_content_type,
        source_object_id=revision_id,
    )
    for idx_doc in qs:
        _qdrant_delete_chunks_for_indexed_doc(idx_doc.id)
        idx_doc.delete()


def _cleanup_indexed_for_other_revisions(document_id, current_revision_id, revision_model):
    """
    Delete IndexedDocuments for every OTHER revision of the same ManagedDocument.
    Ensures only the currently published revision is searchable.
    """
    from django.contrib.contenttypes.models import ContentType
    from .models import IndexedDocument

    other_rev_ids = list(
        revision_model.objects.filter(document_id=document_id)
        .exclude(id=current_revision_id)
        .values_list("id", flat=True)
    )
    if not other_rev_ids:
        return

    ct = ContentType.objects.get_for_model(revision_model)
    qs = IndexedDocument.objects.filter(
        source_content_type=ct,
        source_object_id__in=other_rev_ids,
    )
    for idx_doc in qs:
        _qdrant_delete_chunks_for_indexed_doc(idx_doc.id)
        idx_doc.delete()


def _ingest_revision_content(revision_id, revision_model):
    """(Re-)index a DocumentRevision: clean stale chunks, create IndexedDocument, ingest."""
    from django.contrib.contenttypes.models import ContentType
    from django.core.files.base import ContentFile
    from .models import IndexedDocument
    from .tasks import ingest_document

    try:
        revision = revision_model.objects.select_related("document").get(id=revision_id)
    except revision_model.DoesNotExist:
        return

    if not (revision.content or "").strip():
        logger.info("document_revision_empty_skipping", revision_id=str(revision_id))
        return

    ct = ContentType.objects.get_for_model(revision_model)

    _cleanup_indexed_for_revision(revision.id, ct)
    _cleanup_indexed_for_other_revisions(revision.document_id, revision.id, revision_model)

    doc_name = (revision.document.name or str(revision.document_id))[:80].replace("/", "_")
    filename = f"policy-{doc_name}-rev{revision.version_number}.md"
    file = ContentFile(revision.content.encode("utf-8"), name=filename)

    # Chat extractors handle text/plain (and PDF) but not text/markdown.
    # Revision content is stored as a TextField, so text/plain is correct.
    indexed = IndexedDocument.objects.create(
        folder=revision.folder,
        file=file,
        filename=filename,
        content_type="text/plain",
        source_type=IndexedDocument.SourceType.CUSTOM,
        source_content_type=ct,
        source_object_id=revision.id,
    )
    ingest_document(str(indexed.id))
    logger.info(
        "auto_queued_document_revision_for_indexing",
        document_id=str(revision.document_id),
        revision_id=str(revision.id),
        indexed_document_id=str(indexed.id),
        filename=filename,
    )


def _connect_document_revision_signal(ff_is_enabled):
    """
    Connect signals to keep ManagedDocument policies in sync with the RAG store.

    Lifecycle handled:
      - revision saved with status=PUBLISHED -> re-ingest (delete old chunks first,
        and clear any other indexed revisions of the same document so only the
        currently published one is searchable)
      - revision saved with status != PUBLISHED -> delete its chunks (covers
        Draft, In review, Change requested, Validated-not-yet-published, Deprecated)
      - revision deleted -> delete its chunks
      - ManagedDocument deleted -> cascades to revisions, which fire post_delete
    """
    from django.apps import apps

    try:
        DocumentRevision = apps.get_model("doc_management", "DocumentRevision")
    except LookupError:
        logger.warning(
            "DocumentRevision model not found, skipping policy auto-ingest signal"
        )
        return

    PUBLISHED = DocumentRevision.Status.PUBLISHED

    @receiver(post_save, sender=DocumentRevision, weak=False)
    def on_document_revision_save(sender, instance, **kwargs):
        if not ff_is_enabled("chat_mode"):
            return

        from django.contrib.contenttypes.models import ContentType
        from django.db import transaction

        revision_id = str(instance.id)
        ct = ContentType.objects.get_for_model(DocumentRevision)

        if instance.status == PUBLISHED:
            transaction.on_commit(
                lambda: _ingest_revision_content(revision_id, DocumentRevision)
            )
        else:
            # Demoted from published, or never published. Retire its chunks.
            transaction.on_commit(
                lambda: _cleanup_indexed_for_revision(revision_id, ct)
            )

    @receiver(post_delete, sender=DocumentRevision, weak=False)
    def on_document_revision_delete(sender, instance, **kwargs):
        if not ff_is_enabled("chat_mode"):
            return

        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(DocumentRevision)
        _cleanup_indexed_for_revision(instance.id, ct)


# Do NOT call connect_signals() at module level.
# It is called from ChatConfig.ready() in apps.py, which ensures
# all models are fully loaded before we try to resolve them.
