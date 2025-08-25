from fastapi import APIRouter, Header, HTTPException
import os
import httpx
from packaging import version as semver
from pathlib import Path
from .. import config

router = APIRouter()

APP_NAME = os.getenv("APP_NAME", "telemetry-api")

def get_version_from_file():
    """Read version from TELEMETRY_VERSION env var, fallback to VERSION file, then config"""
    # Primary: TELEMETRY_VERSION env var (set by Docker build)
    version = os.getenv("TELEMETRY_VERSION")
    if version:
        return version
    
    # Secondary: VERSION file at repo root
    try:
        version_file = Path(__file__).parent.parent.parent / "VERSION"
        if version_file.exists():
            with open(version_file, 'r') as f:
                version = f.read().strip()
                if version:
                    return version
    except Exception:
        pass
    
    # Fallback to environment variable
    from ..config import API_VERSION
    return os.getenv("APP_VERSION", API_VERSION)

APP_VERSION = get_version_from_file()
GIT_SHA = os.getenv("GIT_SHA", "unknown")
IMAGE = os.getenv("IMAGE", "shvin/telemetry-api")
UPDATE_CHECK_ENABLED = os.getenv("UPDATE_CHECK_ENABLED", "true").lower() == "true"
DOCKERHUB_REPO = os.getenv("DOCKERHUB_REPO", IMAGE)  # e.g. shvin/telemetry-api
DOCKERHUB_TAG = os.getenv("DOCKERHUB_TAG", APP_VERSION)

@router.get("/version")
def get_version():
    image_version = (
        getattr(config, "APP_VERSION", None)
        or getattr(config, "API_VERSION", None)
        or getattr(config, "IMAGE_VERSION", None)
        or os.getenv("IMAGE_VERSION")
        or "dev"
    )
    git_sha = os.getenv("GIT_SHA", getattr(config, "GIT_SHA", "unknown"))
    image_digest = os.getenv("IMAGE_DIGEST", getattr(config, "IMAGE_DIGEST", "unknown"))
    image = os.getenv("IMAGE", getattr(config, "IMAGE", "unknown"))
    image_tag = os.getenv("DOCKERHUB_TAG", getattr(config, "DOCKERHUB_TAG", image_version))
    return {
        "status": "ok",
        "api_version": "v1",
        "image_version": image_version,
        # legacy keys many tests assert:
        "version": image_version,  # Return numeric version (no "v" prefix)
        "git_sha": (git_sha[:7] if isinstance(git_sha, str) else "unknown"),
        "image": image,
        "image_tag": image_tag,
        "image_digest": image_digest,
    }

async def _fetch_latest_tag(repo: str) -> str:
    # Docker Hub tags (public) – minimal call, page_size=1 gives latest by date
    url = f"https://hub.docker.com/v2/repositories/{repo}/tags?page_size=1"
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        if not results:
            raise RuntimeError("No tags found")
        return results[0]["name"]

@router.get("/updates/check")
async def check_updates():
    if not UPDATE_CHECK_ENABLED:
        return {"enabled": False, "status": "disabled"}
    latest = await _fetch_latest_tag(DOCKERHUB_REPO)
    current = DOCKERHUB_TAG
    try:
        newer = semver.parse(latest) > semver.parse(current)
    except Exception:
        # Fallback to string compare if tags aren't semver
        newer = latest != current
    return {
        "enabled": True,
        "current": current,
        "latest": latest,
        "update_available": newer,
    }
