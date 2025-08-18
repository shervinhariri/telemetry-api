#!/usr/bin/env python3
import os, json, requests

API = os.environ.get("API_BASE_URL", "http://localhost:80")
KEY = os.environ.get("API_KEY", "TEST_KEY")
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


def post(path, body):
    return requests.post(f"{API}{path}", headers=HEADERS, data=json.dumps(body), timeout=10)


def get(path, params=None, extra_headers=None):
    h = dict(HEADERS)
    if extra_headers:
        h.update(extra_headers)
    return requests.get(f"{API}{path}", headers=h, params=params, timeout=10)


def scenario_valid_low_risk():
    return {
        "name": "valid_low_risk",
        "req": {
            "collector_id": "tester",
            "format": "flows.v1",
            "records": [
                {
                    "ts": 1723351200.456,
                    "src_ip": "10.0.0.10",
                    "dst_ip": "8.8.8.8",
                    "src_port": 54000,
                    "dst_port": 53,
                    "protocol": "udp",
                    "bytes": 120,
                    "packets": 1,
                }
            ],
        },
        "expect_status": 200,
    }


def scenario_valid_higher_risk():
    return {
        "name": "valid_higher_risk",
        "req": {
            "collector_id": "tester",
            "format": "flows.v1",
            "records": [
                {
                    "ts": 1723351201.789,
                    "src_ip": "10.0.0.11",
                    "dst_ip": "1.1.1.1",
                    "src_port": 44444,
                    "dst_port": 3389,
                    "protocol": "tcp",
                    "bytes": 250000,
                    "packets": 120,
                }
            ],
        },
        "expect_status": 200,
    }


def scenario_missing_field():
    bad = {
        "collector_id": "tester",
        "format": "flows.v1",
        "records": [
            {
                "ts": 1723351202.123,
                "src_ip": "10.0.0.12",
                # missing dst_ip
                "src_port": 55555,
                "dst_port": 80,
                "protocol": "tcp",
                "bytes": 256,
                "packets": 2,
            }
        ],
    }
    return {"name": "missing_field", "req": bad, "expect_status": 400}


def scenario_bad_format():
    bad = {"collector_id": "tester", "format": "unknown.v9", "records": []}
    return {"name": "bad_format", "req": bad, "expect_status": 400}


def scenario_bulk_batch(n: int = 200):
    recs = []
    for i in range(n):
        recs.append(
            {
                "ts": 1723351200.0 + i * 0.001,
                "src_ip": f"10.0.1.{i % 250}",
                "dst_ip": "9.9.9.9",
                "src_port": 10000 + i % 5000,
                "dst_port": 80 if i % 2 == 0 else 443,
                "protocol": "tcp",
                "bytes": 1500 + i,
                "packets": 3 + (i % 5),
            }
        )
    return {
        "name": "bulk_batch_200",
        "req": {"collector_id": "tester", "format": "flows.v1", "records": recs},
        "expect_status": 200,
    }


def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return {"text": resp.text[:500]}


def run():
    scenarios = [
        scenario_valid_low_risk(),
        scenario_valid_higher_risk(),
        scenario_missing_field(),
        scenario_bad_format(),
        scenario_bulk_batch(),
    ]
    results = []
    for sc in scenarios:
        try:
            r = post("/v1/ingest", sc["req"])
            results.append(
                {
                    "scenario": sc["name"],
                    "status": r.status_code,
                    "ok": r.status_code == sc["expect_status"],
                    "resp": safe_json(r),
                }
            )
        except Exception as e:
            results.append({"scenario": sc["name"], "status": "ERR", "ok": False, "resp": str(e)})

    # Check admin feed + ETag
    try:
        ar = get("/v1/admin/requests", params={"exclude_monitoring": "true", "limit": "5"})
        etag = ar.headers.get("ETag", "")
        recent = safe_json(ar)
    except Exception as e:
        etag, recent = "", {"error": str(e)}

    # Metrics sample
    try:
        m = get("/v1/metrics", params={"window": "900"})
        metrics = safe_json(m)
    except Exception as e:
        metrics = {"error": str(e)}

    print(
        json.dumps(
            {
                "api": API,
                "results": results,
                "admin_requests_sample": recent,
                "admin_requests_etag": etag,
                "metrics_sample": metrics,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    run()


