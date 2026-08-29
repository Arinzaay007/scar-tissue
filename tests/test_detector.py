from agent.detector import scan


def test_off_by_one():
    f = scan("for i in range(len(users)):\n    handle(users[i])")
    sigs = {x["signature"] for x in f}
    assert "off-by-one" in sigs


def test_bare_except():
    f = scan("try:\n    go()\nexcept:\n    return None")
    assert "bare-except" in {x["signature"] for x in f}


def test_except_pass():
    f = scan("try:\n    go()\nexcept FileNotFoundError:\n    pass")
    assert "except-pass" in {x["signature"] for x in f}


def test_mutable_default():
    f = scan("def add(name, members=[]):\n    members.append(name)")
    assert "mutable-default" in {x["signature"] for x in f}


def test_unchecked_get():
    f = scan("cfg.get('plan').billing")
    assert "unchecked-get" in {x["signature"] for x in f}


def test_dedupe():
    # identical evidence (same line twice) dedupes to one finding
    code = "for i in range(len(a)):\n    x = a[i]\nfor i in range(len(a)):\n    y = a[i]"
    offs = [x for x in scan(code) if x["signature"] == "off-by-one"]
    assert len(offs) == 1


def test_distinct_locations_are_distinct_findings():
    code = "for i in range(len(a)):\n    x = a[i]\nfor j in range(len(b)):\n    y = b[j]"
    offs = [x for x in scan(code) if x["signature"] == "off-by-one"]
    assert len(offs) == 2  # two different loops -> two findings


def test_clean_code_has_no_findings():
    assert scan("def ok(seq):\n    for item in seq:\n        print(item)") == []
