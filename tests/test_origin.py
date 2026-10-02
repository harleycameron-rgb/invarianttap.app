import pytest

from origin import OriginMissing, resolve_origin


def test_resolve_origin_prefers_cli_value(monkeypatch):
    monkeypatch.setenv("INVARIANTTAP_ORIGIN", "environment-origin")

    assert resolve_origin("cli-origin") == "cli-origin"


def test_resolve_origin_uses_environment(monkeypatch):
    monkeypatch.setenv("INVARIANTTAP_ORIGIN", "environment-origin")

    assert resolve_origin() == "environment-origin"


@pytest.mark.parametrize("cli_value", [None, ""])
def test_resolve_origin_requires_value(monkeypatch, cli_value):
    monkeypatch.delenv("INVARIANTTAP_ORIGIN", raising=False)

    with pytest.raises(OriginMissing, match="Refusing to mint without an origin"):
        resolve_origin(cli_value)
