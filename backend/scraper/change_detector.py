from datetime import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from backend.models import ScrapedDocument, ScrapedDocumentVersion
from backend.scraper.hasher import compute_content_hash


def process_scraped_documents(
    db: Session,
    scraped_items: List[Dict[str, Any]],
    mark_removed_missing: bool = False
) -> Dict[str, Any]:
    """
    Compares newly scraped raw document records against existing SQL records using SHA-256 hashes.
    Performs SQL updates and creates version audit entries in scraped_document_versions.
    
    Returns a dictionary of statistics and collections of NEW, UPDATED, and UNCHANGED documents.
    """
    now = datetime.utcnow()
    
    new_docs: List[ScrapedDocument] = []
    updated_docs: List[ScrapedDocument] = []
    unchanged_docs: List[ScrapedDocument] = []
    removed_docs: List[ScrapedDocument] = []
    failed_docs: List[Dict[str, Any]] = []

    scraped_canonical_urls = set()

    for item in scraped_items:
        url = item.get("url")
        canonical_url = item.get("canonical_url") or url
        scraped_canonical_urls.add(canonical_url)

        # Raw content for hashing & storage
        content = item.get("content") or item.get("raw_text") or ""
        content_hash = item.get("content_hash") or compute_content_hash(content)

        # Search existing record by canonical URL or exact URL
        existing_doc = (
            db.query(ScrapedDocument)
            .filter(
                (ScrapedDocument.canonical_url == canonical_url) | (ScrapedDocument.url == url)
            )
            .first()
        )

        if existing_doc is None:
            # 1. NEW Document
            doc = ScrapedDocument(
                url=url,
                canonical_url=canonical_url,
                title=item.get("title") or url,
                content=content,
                content_type=item.get("content_type", "html"),
                mime_type=item.get("mime_type", "text/html"),
                source_type=item.get("source_type", "web_page"),
                parent_url=item.get("parent_url"),
                depth=item.get("depth", 0),
                content_hash=content_hash,
                etag=item.get("etag"),
                last_modified=item.get("last_modified"),
                first_seen_at=now,
                last_scraped_at=now,
                last_changed_at=now,
                status="NEW",
                processing_status="PENDING",
                version=1,
                is_active=True
            )
            db.add(doc)
            db.flush()  # populate doc.id

            # Save initial version entry in scraped_document_versions
            version_record = ScrapedDocumentVersion(
                document_id=doc.id,
                version=1,
                content=content,
                content_hash=content_hash,
                scraped_at=now,
                changed_at=now,
                change_type="NEW"
            )
            db.add(version_record)
            new_docs.append(doc)
            print(f"[CHANGE DETECTOR] NEW document added: {url} (v1)")

        else:
            # Existing Document - Check Hash
            if existing_doc.content_hash == content_hash:
                # 2. UNCHANGED Document
                existing_doc.status = "UNCHANGED"
                existing_doc.last_scraped_at = now
                existing_doc.is_active = True
                unchanged_docs.append(existing_doc)
                print(f"[CHANGE DETECTOR] UNCHANGED document skipped: {url} (Hash {content_hash[:8]})")
            else:
                # 3. UPDATED Document
                old_version = existing_doc.version
                new_version = old_version + 1

                existing_doc.version = new_version
                existing_doc.content = content
                existing_doc.content_hash = content_hash
                existing_doc.title = item.get("title") or existing_doc.title
                existing_doc.etag = item.get("etag") or existing_doc.etag
                existing_doc.last_modified = item.get("last_modified") or existing_doc.last_modified
                existing_doc.last_scraped_at = now
                existing_doc.last_changed_at = now
                existing_doc.status = "UPDATED"
                existing_doc.processing_status = "PENDING"
                existing_doc.is_active = True

                # Save new version audit record in scraped_document_versions
                version_record = ScrapedDocumentVersion(
                    document_id=existing_doc.id,
                    version=new_version,
                    content=content,
                    content_hash=content_hash,
                    scraped_at=now,
                    changed_at=now,
                    change_type="UPDATED"
                )
                db.add(version_record)
                updated_docs.append(existing_doc)
                print(f"[CHANGE DETECTOR] UPDATED document detected: {url} (v{old_version} -> v{new_version})")

    # 4. REMOVED Documents detection (optional, when doing full crawl)
    if mark_removed_missing and scraped_canonical_urls:
        active_db_docs = (
            db.query(ScrapedDocument)
            .filter(ScrapedDocument.is_active == True)
            .all()
        )
        for doc in active_db_docs:
            if doc.canonical_url not in scraped_canonical_urls and doc.url not in scraped_canonical_urls:
                doc.is_active = False
                doc.status = "REMOVED"
                doc.last_changed_at = now
                
                version_record = ScrapedDocumentVersion(
                    document_id=doc.id,
                    version=doc.version,
                    content=doc.content,
                    content_hash=doc.content_hash,
                    scraped_at=now,
                    changed_at=now,
                    change_type="REMOVED"
                )
                db.add(version_record)
                removed_docs.append(doc)
                print(f"[CHANGE DETECTOR] REMOVED document marked inactive: {doc.url}")

    db.commit()

    return {
        "new_docs": new_docs,
        "updated_docs": updated_docs,
        "unchanged_docs": unchanged_docs,
        "removed_docs": removed_docs,
        "counts": {
            "new": len(new_docs),
            "updated": len(updated_docs),
            "unchanged": len(unchanged_docs),
            "removed": len(removed_docs),
        }
    }
