import pytest
from fastapi.testclient import TestClient

import main
from repository import PredictionRepository
from service import ModerationService


PAYLOAD = {
    "seller_id": 1,
    "is_verified_seller": False,
    "item_id": 10,
    "name": "Велосипед",
    "description": "Продам велосипед",
    "category": 2,
    "images_qty": 0,
}
SCENARIOS = [(True, 0, False), (True, 1, False), (True, 5, False),
             (False, 0, True), (False, 1, False), (False, 5, False)]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "service", ModerationService(PredictionRepository()))
    with TestClient(main.app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


@pytest.mark.parametrize("verified,images,expected", SCENARIOS)
def test_predict(client, verified, images, expected):
    response = client.post("/predict", json={**PAYLOAD, "is_verified_seller": verified, "images_qty": images})
    assert response.status_code == 200
    assert response.json() is expected  # именно JSON boolean, без объекта-обёртки
    assert main.service.repository.get_prediction(PAYLOAD["item_id"]) is expected


@pytest.mark.parametrize("field", PAYLOAD)
def test_missing_field(client, field):
    body = {key: value for key, value in PAYLOAD.items() if key != field}
    response = client.post("/predict", json=body)
    assert response.status_code == 400
    assert any(error["field"] == field for error in response.json()["detail"])


@pytest.mark.parametrize("field,value", [
    ("seller_id", "1"), ("seller_id", True), ("seller_id", 1.0), ("seller_id", 0), ("seller_id", -1),
    ("item_id", "10"), ("item_id", False), ("item_id", 1.5), ("item_id", 0), ("item_id", -1),
    ("category", "2"), ("category", True), ("category", 2.0), ("category", 0), ("category", -1),
    ("images_qty", "0"), ("images_qty", False), ("images_qty", 1.0), ("images_qty", -1),
    ("is_verified_seller", "false"), ("is_verified_seller", 0), ("is_verified_seller", 1),
    ("name", 123), ("name", ""), ("name", "   "), ("name", []),
    ("description", 123), ("description", ""), ("description", "\n\t"), ("description", {}),
] + [(field, None) for field in PAYLOAD])
def test_invalid_value(client, field, value):
    response = client.post("/predict", json={**PAYLOAD, field: value})
    assert response.status_code == 400
    assert any(error["field"] == field for error in response.json()["detail"])


@pytest.mark.parametrize("body", [{}, [], "text"])
def test_invalid_body(client, body):
    assert client.post("/predict", json=body).status_code == 400


def test_missing_body(client):
    assert client.post("/predict").status_code == 400


def test_malformed_json(client):
    response = client.post("/predict", content="{broken", headers={"Content-Type": "application/json"})
    assert response.status_code == 400


def test_unknown_field(client):
    assert client.post("/predict", json={**PAYLOAD, "unexpected": 1}).status_code == 400


@pytest.mark.parametrize("layer", ["service", "repository"])
def test_internal_error(client, monkeypatch, layer):
    def fail(*args, **kwargs):
        raise RuntimeError("private internal details")

    target, method = (main.service, "predict") if layer == "service" else (main.service.repository, "save_prediction")
    monkeypatch.setattr(target, method, fail)
    response = client.post("/predict", json=PAYLOAD)
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "private internal details" not in response.text


@pytest.mark.parametrize("verified,images,expected", SCENARIOS)
def test_service(verified, images, expected):
    repository = PredictionRepository()
    result = ModerationService(repository).predict(10, verified, images)
    assert result is expected
    assert repository.get_prediction(10) is expected


def test_repository():
    repository = PredictionRepository()
    assert repository.get_prediction(10) is None
    repository.save_prediction(10, True)
    repository.save_prediction(10, False)
    assert repository.get_prediction(10) is False


def test_openapi(client):
    operation = client.get("/openapi.json").json()["paths"]["/predict"]["post"]
    assert set(operation["responses"]) == {"200", "400", "500"}
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["type"] == "boolean"
