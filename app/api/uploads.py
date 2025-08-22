from fastapi import APIRouter, UploadFile, File, HTTPException
import os, uuid, hashlib, shutil

router = APIRouter(prefix="/v1/upload", tags=["upload"])
DATA_DIR = os.getenv("ENRICH_DATA_DIR", "/data/enrichment")

@router.post("/geoip")
async def upload_geoip(f: UploadFile = File(...)):
    os.makedirs(DATA_DIR, exist_ok=True)
    if not f.filename.endswith(".mmdb"):
        raise HTTPException(400, "GeoIP upload must be .mmdb")

    blob_id = str(uuid.uuid4())
    dst = os.path.join(DATA_DIR, blob_id + "_" + f.filename)
    with open(dst, "wb") as out:
        shutil.copyfileobj(f.file, out)

    checksum = hashlib.sha256(open(dst,"rb").read()).hexdigest()
    size = os.path.getsize(dst)
    # TODO: persist in uploaded_blobs table if you have it; for now return path
    return {"blob_id": blob_id, "path": dst, "size": size, "checksum": checksum}
