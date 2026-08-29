import pytest

from agent.memory import ScarTissueMemory, CATEGORY


@pytest.fixture
def mem(tmp_path):
    m = ScarTissueMemory(tmp_path / "t.db")
    yield m


def test_upsert_increments_count(mem):
    r1 = mem.upsert_pattern("off-by-one", lang="python", suggestion="use enumerate()")
    assert r1["new"] is True
    assert r1["body"]["count"] == 1

    r2 = mem.upsert_pattern("off-by-one", lang="python", suggestion="use enumerate()")
    assert r2["new"] is False
    assert r2["body"]["count"] == 2


def test_single_source_of_truth(mem):
    mem.upsert_pattern("x", lang="python", suggestion="s")
    mem.upsert_pattern("x", lang="python", suggestion="s")
    assert len(mem.list_patterns()) == 1


def test_cool_down_moves_to_archive(mem):
    mem.upsert_pattern("off-by-one", lang="python", suggestion="s")
    mem.cool_down("off-by-one", reason="no repeats")
    assert mem.get_pattern("off-by-one") is None
    assert mem.list_patterns() == []


def test_cool_down_unknown_raises(mem):
    with pytest.raises(KeyError):
        mem.cool_down("ghost", reason="n/a")


def test_resurface_reopens_with_history(mem):
    mem.upsert_pattern("off-by-one", lang="python", suggestion="s")  # count 1
    mem.upsert_pattern("off-by-one", lang="python", suggestion="s")  # count 2
    pat = mem.get_pattern("off-by-one")
    mem.cool_down("off-by-one", reason="no repeats")
    mem.resurface("off-by-one", lang="python", suggestion="s",
                  prior_count=pat["body"]["count"])
    reopened = mem.get_pattern("off-by-one")
    assert reopened["body"]["count"] == 3
    assert reopened["body"]["resurfaced"] is True


def test_journal_records_tier_moves(mem):
    mem.upsert_pattern("off-by-one", lang="python", suggestion="s")
    mem.cool_down("off-by-one", reason="no repeats")
    mem.resurface("off-by-one", lang="python", suggestion="s", prior_count=1)
    acted = [" ".join(ev.get("acted") or []) for ev in mem.read_journal()]
    assert any("WARM->ARCHIVE" in a for a in acted)
    assert any("ARCHIVE->WARM" in a for a in acted)


def test_recall_search(mem):
    mem.upsert_pattern("off-by-one", lang="python", suggestion="use enumerate()")
    assert mem.recall("off-by-one") != []
    assert mem.recall("enumerate") != []
    assert mem.recall("zzz-nothing") == []


def test_multi_tenant_isolation(tmp_path):
    a = ScarTissueMemory(tmp_path / "a.db")
    b = ScarTissueMemory(tmp_path / "b.db")
    a.upsert_pattern("off-by-one", lang="python", suggestion="s")
    assert b.list_patterns() == []
