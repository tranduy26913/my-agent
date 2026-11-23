"""Khung API: /healthz không đụng DB, /readyz phản ánh đúng tình trạng DB. Không cần Postgres."""

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.main import create_app


class _OkDb:
    def execute(self, *_a, **_k):
        return 1


class _DownDb:
    def execute(self, *_a, **_k):
        raise ConnectionError("password=secret host=10.0.0.5")  # chi tiết này không được lộ ra response


@pytest.fixture
def app():
    return create_app()


def test_healthz_khong_can_db(app):
    def boom():
        raise AssertionError("/healthz không được mở session DB")
        yield  # pragma: no cover

    app.dependency_overrides[get_db] = boom
    r = TestClient(app).get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_readyz_db_song(app):
    app.dependency_overrides[get_db] = lambda: _OkDb()
    r = TestClient(app).get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": "up"}


def test_readyz_db_sap_tra_503_va_khong_lo_chi_tiet(app):
    app.dependency_overrides[get_db] = lambda: _DownDb()
    r = TestClient(app).get("/readyz")
    assert r.status_code == 503
    assert r.json() == {"status": "unavailable", "db": "down"}
    assert "secret" not in r.text and "10.0.0.5" not in r.text


def test_openapi_co_cac_duong_dan_health(app):
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    assert "/healthz" in paths and "/readyz" in paths
