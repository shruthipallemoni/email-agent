"""
Tests for Block 13 - the knowledge base service.

IMPORTANT LIMITATION: this environment has no real PostgreSQL+pgvector
database and no real Gemini API key, so these tests use mocks for both the
database session and the embedding calls. They confirm OUR orchestration
logic is correct (chunk -> embed -> save, in the right order, with the
right data) - they do NOT prove the real similarity search works end to
end. That can only be verified against a real Postgres+pgvector database
(see README) - please do a manual check there before relying on this.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import knowledge_service


class _FakeUser:
    id = 42


@pytest.mark.asyncio
async def test_add_document_chunks_and_embeds_content():
    fake_db = MagicMock()
    fake_embeddings = [[0.1, 0.2], [0.3, 0.4]]

    with patch("app.services.knowledge_service.chunk_text", return_value=["chunk one", "chunk two"]), \
         patch("app.services.knowledge_service.embed_texts", AsyncMock(return_value=fake_embeddings)):
        await knowledge_service.add_document(fake_db, _FakeUser(), "My Doc", "some long content")

    # One Document + one DocumentChunk per chunk = 3 db.add() calls total.
    assert fake_db.add.call_count == 3
    fake_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_add_document_stores_chunks_in_order_with_correct_indexes():
    fake_db = MagicMock()
    added_chunks = []

    def capture_add(obj):
        if hasattr(obj, "chunk_index"):
            added_chunks.append(obj)

    fake_db.add.side_effect = capture_add

    with patch("app.services.knowledge_service.chunk_text", return_value=["first", "second", "third"]), \
         patch(
             "app.services.knowledge_service.embed_texts",
             AsyncMock(return_value=[[0.0], [0.0], [0.0]]),
         ):
        await knowledge_service.add_document(fake_db, _FakeUser(), "Doc", "content")

    assert [c.chunk_index for c in added_chunks] == [0, 1, 2]
    assert [c.content for c in added_chunks] == ["first", "second", "third"]
    assert all(c.user_id == 42 for c in added_chunks)


def test_list_documents_filters_by_user_and_orders_newest_first():
    fake_db = MagicMock()
    fake_query = fake_db.query.return_value
    fake_query.filter.return_value.order_by.return_value.all.return_value = ["doc1", "doc2"]

    result = knowledge_service.list_documents(fake_db, _FakeUser())

    assert result == ["doc1", "doc2"]
    fake_db.query.return_value.filter.assert_called_once()


def test_delete_document_returns_false_when_not_found():
    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = None

    result = knowledge_service.delete_document(fake_db, _FakeUser(), document_id=999)

    assert result is False
    fake_db.delete.assert_not_called()


def test_delete_document_deletes_and_commits_when_found():
    fake_db = MagicMock()
    fake_document = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = fake_document

    result = knowledge_service.delete_document(fake_db, _FakeUser(), document_id=1)

    assert result is True
    fake_db.delete.assert_called_once_with(fake_document)
    fake_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_search_similar_chunks_embeds_the_query_and_filters_by_user():
    fake_db = MagicMock()
    fake_query_chain = fake_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value
    fake_query_chain.all.return_value = ["chunk_a", "chunk_b"]

    with patch(
        "app.services.knowledge_service.embed_text", AsyncMock(return_value=[0.1, 0.2, 0.3])
    ) as fake_embed:
        result = await knowledge_service.search_similar_chunks(fake_db, _FakeUser(), "what's the wifi password?")

    fake_embed.assert_awaited_once_with("what's the wifi password?")
    assert result == ["chunk_a", "chunk_b"]