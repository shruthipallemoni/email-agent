"""
Lets the user add, browse, and remove documents in their personal
knowledge base - the RAG system the agent searches when drafting replies.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.knowledge import DocumentCreate, DocumentListResponse, DocumentSummary
from app.services import knowledge_service

router = APIRouter()


@router.post("", response_model=DocumentSummary)
async def add_document(
    payload: DocumentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Adds a document to the knowledge base - it gets chunked and embedded for later search."""
    document = await knowledge_service.add_document(db, user, payload.title, payload.content)
    return DocumentSummary(
        id=document.id,
        title=document.title,
        chunk_count=len(document.chunks),
        created_at=document.created_at,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lists every document currently in the user's knowledge base."""
    documents = knowledge_service.list_documents(db, user)
    return DocumentListResponse(
        documents=[
            DocumentSummary(
                id=d.id, title=d.title, chunk_count=len(d.chunks), created_at=d.created_at
            )
            for d in documents
        ]
    )


@router.delete("/{document_id}")
def delete_document(
    document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Removes a document (and its chunks) from the knowledge base."""
    deleted = knowledge_service.delete_document(db, user, document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": True}