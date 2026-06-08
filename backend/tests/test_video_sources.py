import pytest
from fastapi import HTTPException

from app.video_sources import resolve_video_url, validate_upload


def test_resolves_youtube_embed() -> None:
    resolved = resolve_video_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert resolved.source_type == "youtube"
    assert "enablejsapi=1" in resolved.embed_url
    assert not resolved.playable_in_html5


def test_resolves_direct_video() -> None:
    resolved = resolve_video_url("https://cdn.example.com/movie.mp4")
    assert resolved.source_type == "direct"
    assert resolved.playable_in_html5


def test_blocks_localhost_links() -> None:
    with pytest.raises(HTTPException):
        resolve_video_url("http://localhost/movie.mp4")


def test_upload_validation() -> None:
    validate_upload("movie.webm", "video/webm", 1024, 2048)
    with pytest.raises(HTTPException):
        validate_upload("movie.exe", "application/octet-stream", 1024, 2048)
