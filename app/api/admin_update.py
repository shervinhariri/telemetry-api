from fastapi import APIRouter, Header, HTTPException
import os, subprocess

router = APIRouter()
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")  # set for dev-only

def _require_admin(x_admin_token: str | None):
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.post("/admin/update")
def admin_update(x_admin_token: str | None = Header(None)):
    _require_admin(x_admin_token)
    image = os.getenv("IMAGE", "shvin/telemetry-api")
    tag = os.getenv("DOCKERHUB_TAG", "latest")
    # Pull and restart: assumes docker-compose or container orchestrator handles restart
    try:
        out1 = subprocess.check_output(["docker", "pull", f"{image}:{tag}"], stderr=subprocess.STDOUT, text=True)
        return {"ok": True, "pulled": f"{image}:{tag}", "log": out1}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.output)
