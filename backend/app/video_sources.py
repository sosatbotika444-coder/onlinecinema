import ipaddress
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException, status


@dataclass(frozen=True)
class ResolvedVideo:
    source_type: str
    url: str
    embed_url: str | None
    title: str | None
    playable_in_html5: bool


DIRECT_EXTENSIONS = {".mp4", ".webm", ".m4v", ".mov"}
UPLOAD_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}
UPLOAD_CONTENT_TYPES = {
    "video/mp4",
    "video/x-matroska",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
    "application/octet-stream",
}
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only HTTP(S) links are supported")
    host = (parsed.hostname or "").lower()
    if host in BLOCKED_HOSTS or host.endswith(".local"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Local URLs are not allowed")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Private network URLs are not allowed")


def _youtube_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().replace("www.", "")
    if host == "youtu.be":
        return parsed.path.strip("/") or None
    if host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        if parsed.path.startswith("/watch"):
            return parse_qs(parsed.query).get("v", [None])[0]
        match = re.match(r"/(?:embed|shorts)/([^/?#]+)", parsed.path)
        return match.group(1) if match else None
    return None


def _vk_embed(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().replace("www.", "")
    if host not in {"vk.com", "m.vk.com", "vkvideo.ru", "m.vkvideo.ru"}:
        return None
    match = re.search(r"video(-?\d+)_(\d+)", url)
    if not match:
        return url
    oid, video_id = match.groups()
    return f"https://vk.com/video_ext.php?oid={oid}&id={video_id}&hd=2"


def _rutube_embed(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().replace("www.", "")
    if host != "rutube.ru":
        return None
    match = re.search(r"/(?:video|play/embed)/([A-Za-z0-9]+)/?", parsed.path)
    if not match:
        return url
    return f"https://rutube.ru/play/embed/{match.group(1)}"


def resolve_video_url(url: str) -> ResolvedVideo:
    _validate_public_url(url)
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().replace("www.", "")
    path_ext = Path(parsed.path).suffix.lower()

    youtube_id = _youtube_id(url)
    if youtube_id:
        return ResolvedVideo(
            source_type="youtube",
            url=url,
            embed_url=f"https://www.youtube.com/embed/{youtube_id}?enablejsapi=1&playsinline=1",
            title="YouTube video",
            playable_in_html5=False,
        )

    vk_embed = _vk_embed(url)
    if vk_embed:
        return ResolvedVideo("vk", url, vk_embed, "VK Видео", False)

    rutube_embed = _rutube_embed(url)
    if rutube_embed:
        return ResolvedVideo("rutube", url, rutube_embed, "Rutube video", False)

    if path_ext in DIRECT_EXTENSIONS:
        return ResolvedVideo("direct", url, None, Path(parsed.path).name or "Video file", True)

    if host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported video source. Use YouTube, VK Видео, Rutube, or a direct mp4/webm link.",
        )
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid video URL")


def validate_upload(filename: str, content_type: str, size_bytes: int, max_size_bytes: int) -> None:
    extension = Path(filename).suffix.lower()
    if extension not in UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file format")
    if content_type not in UPLOAD_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported content type")
    if size_bytes > max_size_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File is too large")
