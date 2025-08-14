from fastapi import APIRouter, Header, HTTPException
import os
import httpx
from packaging import version as semver

router = APIRouter()

APP_NAME = os.getenv("APP_NAME", "telemetry-api")
APP_VERSION = os.getenv("APP_VERSION", "0.7.2")
GIT_SHA = os.getenv("GIT_SHA", "unknown")
IMAGE = os.getenv("IMAGE", "shvin/telemetry-api")
UPDATE_CHECK_ENABLED = os.getenv("UPDATE_CHECK_ENABLED", "true").lower() == "true"
DOCKERHUB_REPO = os.getenv("DOCKERHUB_REPO", IMAGE)  # e.g. shvin/telemetry-api
DOCKERHUB_TAG = os.getenv("DOCKERHUB_TAG", APP_VERSION)

@router.get("/version")
def get_version():
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "git_sha": GIT_SHA[:7],
        "image": IMAGE,
        "image_tag": DOCKERHUB_TAG,
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
