import socket, threading, time
from fastapi import FastAPI
import uvicorn

PACKETS = 0
BYTES = 0

def udp_loop(host="0.0.0.0", port=2055):
    global PACKETS, BYTES
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((host, port))
    while True:
        data, _addr = s.recvfrom(65535)
        PACKETS += 1
        BYTES += len(data)

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "component": "udp-head"}

@app.get("/stats")
def stats():
    return {"packets": PACKETS, "bytes": BYTES, "port": 2055}

if __name__ == "__main__":
    threading.Thread(target=udp_loop, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8081)
