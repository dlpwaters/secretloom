"""tests/test_web_api.py - Web API integration checks for new parity endpoints."""
import io
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from web.app import _persist_artifact, create_app

FIXTURES = Path(__file__).parent / "fixtures"


def _client():
    app = create_app()
    app.testing = True
    return app.test_client()


def test_home_uses_secretloom_brand_without_remote_assets():
    r = _client().get("/")
    assert r.status_code == 200
    page = r.get_data(as_text=True)
    assert "SecretLoom" in page
    assert "fonts.googleapis.com" not in page
    assert "secretloom.css" in page


def test_health_endpoint_describes_local_engine():
    r = _client().get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["product"] == "SecretLoom"
    assert data["engine"] == "StegoForge"
    assert data["local_only"] is True
    assert data["max_upload_bytes"] == 200 * 1024 * 1024


def test_responses_include_local_security_headers():
    r = _client().get("/")
    assert r.headers["Cache-Control"] == "no-store"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert "Access-Control-Allow-Origin" not in r.headers


def test_artifact_download_uses_opaque_basename_and_rejects_traversal():
    artifact_id = _persist_artifact(b"secretloom-test", ".bin")
    artifact_path = Path(tempfile.gettempdir()) / artifact_id
    try:
        r = _client().get("/artifact", query_string={"id": artifact_id})
        assert r.status_code == 200
        assert r.data == b"secretloom-test"

        blocked = _client().get("/artifact", query_string={"id": f"../{artifact_id}"})
        assert blocked.status_code == 400
    finally:
        artifact_path.unlink(missing_ok=True)


def test_platform_profiles_endpoint():
    c = _client()
    r = c.get("/api/platform-profiles")
    assert r.status_code == 200
    data = r.get_json()
    assert "profiles" in data
    assert "twitter" in data["profiles"]
    assert "facebook" in data["profiles"]


def test_capacity_matrix_endpoint():
    c = _client()
    carrier = (FIXTURES / "sample.png").read_bytes()
    payload = (FIXTURES / "sample.txt").read_bytes()
    r = c.post(
        "/api/capacity-matrix",
        data={
            "file": (io.BytesIO(carrier), "sample.png"),
            "payload": (io.BytesIO(payload), "sample.txt"),
            "depth": "1",
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "rows" in data
    assert len(data["rows"]) > 0


def test_capacity_matrix_rejects_invalid_depth_as_client_error():
    c = _client()
    carrier = (FIXTURES / "sample.png").read_bytes()
    r = c.post(
        "/api/capacity-matrix",
        data={"file": (io.BytesIO(carrier), "sample.png"), "depth": "9"},
        content_type="multipart/form-data",
    )
    assert r.status_code == 400
    assert "between 1 and 4" in r.get_json()["error"]


def test_detect_requires_at_least_one_detector_when_explicitly_disabled():
    c = _client()
    carrier = (FIXTURES / "sample.png").read_bytes()
    r = c.post(
        "/detect",
        data={
            "file": (io.BytesIO(carrier), "sample.png"),
            "chi2": "0",
            "rs": "0",
            "exif": "0",
            "blind": "0",
            "ml": "0",
            "fingerprint": "0",
            "binary": "0",
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data


def test_web_detect_audio_includes_audio_anomaly():
    c = _client()
    audio = (FIXTURES / "sample.wav").read_bytes()
    r = c.post(
        "/detect",
        data={
            "file": (io.BytesIO(audio), "sample.wav"),
            "chi2": "1",
            "rs": "1",
            "exif": "1",
            "blind": "1",
            "ml": "1",
            "fingerprint": "1",
            "binary": "1",
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    methods = [x["method"] for x in r.get_json().get("results", [])]
    assert "audio-anomaly" in methods


def test_web_detect_pdf_includes_pdf_anomaly():
    c = _client()
    pdf = (FIXTURES / "sample.pdf").read_bytes()
    r = c.post(
        "/detect",
        data={
            "file": (io.BytesIO(pdf), "sample.pdf"),
            "chi2": "1",
            "rs": "1",
            "exif": "1",
            "blind": "1",
            "ml": "1",
            "fingerprint": "1",
            "binary": "1",
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    methods = [x["method"] for x in r.get_json().get("results", [])]
    assert "pdf-anomaly" in methods


def test_encode_stream_endpoint_emits_success():
    c = _client()
    carrier = (FIXTURES / "sample.png").read_bytes()
    payload = (FIXTURES / "sample.txt").read_bytes()
    r = c.post(
        "/api/encode-stream",
        data={
            "carrier": (io.BytesIO(carrier), "sample.png"),
            "payload": (io.BytesIO(payload), "sample.txt"),
            "key": "test-key",
            "method": "lsb",
            "depth": "1",
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '"type": "success"' in body


def test_web_encode_artifact_decode_round_trip():
    c = _client()
    carrier = (FIXTURES / "sample.png").read_bytes()
    expected_payload = (FIXTURES / "sample.txt").read_bytes()
    r = c.post(
        "/api/encode-stream",
        data={
            "carrier": (io.BytesIO(carrier), "sample.png"),
            "payload": (io.BytesIO(expected_payload), "sample.txt"),
            "key": "round-trip-key",
            "method": "lsb",
            "depth": "1",
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in r.get_data(as_text=True).splitlines()
        if line.startswith("data: ")
    ]
    completed = next(event for event in events if event["type"] == "success")
    artifact_id = completed["artifact"]
    artifact_path = Path(tempfile.gettempdir()) / artifact_id

    try:
        artifact = c.get("/artifact", query_string={"id": artifact_id})
        assert artifact.status_code == 200
        assert artifact.data.startswith(b"\x89PNG")

        decoded = c.post(
            "/decode",
            data={
                "file": (io.BytesIO(artifact.data), "sample_stego.png"),
                "key": "round-trip-key",
                "method": "lsb",
            },
            content_type="multipart/form-data",
        )
        assert decoded.status_code == 200
        assert decoded.data == expected_payload
    finally:
        artifact_path.unlink(missing_ok=True)
