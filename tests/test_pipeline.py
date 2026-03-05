from patentkit.detect import detect_doc_type
from patentkit.validate import validate_citations


def test_detect_doc_type():
    assert detect_doc_type("United States Patent") == "granted_patent"


def test_validate_citations():
    record={"pages":[{"columns":[{"lines":[{"global_col_number":1,"line_no":1}]}]}]}
    ok=validate_citations("Fact (Col. 1, ll. 1-1)", record)
    bad=validate_citations("Fact (Col. 1, ll. 2-2)", record)
    assert ok["ok"]
    assert not bad["ok"]
