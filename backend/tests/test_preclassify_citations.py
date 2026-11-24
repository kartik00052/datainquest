from daginquest.agent.nodes.verify_citations import citation_ratio
from daginquest.utils.preclassify import preclassify


def test_preclassify_import_error():
    assert preclassify("ModuleNotFoundError: No module named 'x'") == "IMPORT_ERROR"


def test_preclassify_none():
    assert preclassify("all good") is None


def test_citation_ratio():
    log = "line one\nline two"
    assert citation_ratio(["line one", "made up"], log) == 0.5
    assert citation_ratio([], log) == 0.0
