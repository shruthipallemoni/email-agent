"""
Tests for Block 13 - the chunking logic used before embedding documents.
"""

from app.services.chunking_service import chunk_text


def test_short_text_stays_as_one_chunk():
    result = chunk_text("This is a short document.", chunk_size=800)
    assert result == ["This is a short document."]


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_paragraphs_get_grouped_up_to_chunk_size():
    text = "\n\n".join(f"Paragraph {i} " + ("word " * 20) for i in range(10))
    result = chunk_text(text, chunk_size=200, overlap=30)

    assert len(result) > 1
    assert all(len(c) <= 260 for c in result)  # some slack for overlap + paragraph joins


def test_consecutive_chunks_share_overlap_text():
    text = "\n\n".join(f"Paragraph number {i}, some more filler words here." for i in range(6))
    result = chunk_text(text, chunk_size=100, overlap=20)

    assert len(result) > 1
    # the tail of one chunk should reappear at the start of the next
    overlap_text = result[0][-20:]
    assert overlap_text in result[1]


def test_a_single_huge_paragraph_gets_hard_split():
    huge = "x" * 2000
    result = chunk_text(huge, chunk_size=500, overlap=50)

    assert len(result) > 1
    assert all(len(c) <= 500 for c in result)
    # nothing should be lost - every chunk's unique content should be
    # recoverable by joining (allowing for the overlap duplication)
    assert "".join(result)[:100] == huge[:100]