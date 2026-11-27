import pytest

from app.core.logging import route_template


@pytest.mark.parametrize(
    ("path", "route", "expected"),
    [
        ("/api/notes/abc", "/notes/{note_id}", "/api/notes/{note_id}"),
        ("/api/notes/abc/document", "/notes/{note_id}/document", "/api/notes/{note_id}/document"),
        ("/api/health", "/health", "/api/health"),
        ("/notes/abc", "/notes/{note_id}", "/notes/{note_id}"),
        ("/anything", None, "unmatched"),
    ],
)
def test_the_logged_route_keeps_the_router_prefix_and_hides_the_values(path, route, expected):
    assert route_template(path, route) == expected
