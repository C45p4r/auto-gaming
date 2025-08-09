from app.memory.store import Fact, MemoryStore


def test_memory_add_and_search_roundtrip(tmp_path) -> None:
    db_path = tmp_path / "mem.sqlite3"
    store = MemoryStore(db_path=str(db_path))
    ids = store.add_facts(
        [
            Fact(
                id=None,
                title="Best farming stages",
                source_url="https://example.com/a",
                summary="Stage 1-10 is efficient for beginner mats.",
            ),
            Fact(
                id=None,
                title="Arena tips",
                source_url="https://example.com/b",
                summary="Use speed lead and single-target nukers.",
            ),
        ]
    )
    assert len(ids) == 2
    results = store.search("beginner mats stage")
    assert results, "Expected at least one result"
    assert any("farming" in r.title.lower() for r in results)
