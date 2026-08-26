"""
The main RAG (Retrieval-Augmented Generation) service: lets a user add
documents to their personal knowledge base (project notes, FAQs, policies
- anything they want the agent to be able to reference), and lets the
agent search that knowledge base by MEANING (not just keywords) when
drafting a reply.

How search works, in plain terms: every chunk of every document was
converted into an embedding (a list of numbers representing its meaning)
when it was added. To search, we convert the SEARCH QUERY into an
embedding the same way, then ask PostgreSQL (via the pgvector extension)
for the chunks whose embeddings are numerically closest to the query's
embedding - "closest" corresponds to "most similar in meaning".
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.services.chunking_service import chunk_text
from app.services.embedding_service import embed_text, embed_texts


async def add_document(db: Session, user: User, title: str, content: str) -> Document:
    """Splits a document into chunks, embeds each one, and saves it all."""
    document = Document(user_id=user.id, title=title)
    db.add(document)
    db.flush()  # assigns document.id without fully committing yet

    chunks = chunk_text(content)
    embeddings = await embed_texts(chunks)

    for index, (chunk_content, embedding) in enumerate(zip(chunks, embeddings)):
        db.add(
            DocumentChunk(
                document_id=document.id,
                user_id=user.id,
                chunk_index=index,
                content=chunk_content,
                embedding=embedding,
            )
        )

    db.commit()
    db.refresh(document)
    return document


def list_documents(db: Session, user: User) -> List[Document]:
    return (
        db.query(Document)
        .filter(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


def get_document(db: Session, user: User, document_id: int) -> Optional[Document]:
    return (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user.id)
        .first()
    )


def delete_document(db: Session, user: User, document_id: int) -> bool:
    document = get_document(db, user, document_id)
    if not document:
        return False
    db.delete(document)  # cascades to delete its chunks too (see Document model)
    db.commit()
    return True


async def search_similar_chunks(
    db: Session, user: User, query_text: str, top_k: int = 4
) -> List[DocumentChunk]:
    """
    Finds the `top_k` chunks (across all of this user's documents) that
    are most relevant to `query_text`, ranked by similarity of meaning.
    Returns an empty list if the user has no documents yet - RAG is
    optional enrichment, never a requirement for the agent to work.
    """
    query_embedding = await embed_text(query_text)

    return (
        db.query(DocumentChunk)
        .filter(DocumentChunk.user_id == user.id)
        # cosine_distance: 0 means identical meaning, 2 means opposite -
        # sorting ascending gives the most similar chunks first.
        .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
        .all()
    )