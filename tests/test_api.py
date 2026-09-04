from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["records_available"] == 500


def test_summary_endpoint():
    response = client.get("/summary")
    body = response.json()
    assert response.status_code == 200
    assert body["total_transactions"] == 500
    assert body["matched_transactions"] == 202


def test_transaction_retrieval_and_missing_transaction():
    response = client.get("/transactions/TXN0001")
    assert response.status_code == 200
    assert response.json()["transaction_id"] == "TXN0001"
    assert "risk_score" in response.json()

    missing = client.get("/transactions/DOES_NOT_EXIST")
    assert missing.status_code == 404


def test_transaction_filtering_and_pagination():
    response = client.get("/transactions", params={"final_status": "MATCHED", "page_size": 5})
    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 202
    assert len(body["items"]) == 5
    assert all(item["final_status"] == "MATCHED" for item in body["items"])


def test_exception_filtering():
    response = client.get("/exceptions", params={"exception_type": "PAYMENT_FAILED"})
    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 10
    assert all(item["is_exception"] for item in body["items"])


def test_invalid_pagination_is_rejected():
    response = client.get("/transactions", params={"page": 0})
    assert response.status_code == 422


def test_investigation_endpoint_uses_grounded_fallback():
    response = client.post("/transactions/TXN0001/investigate")
    body = response.json()
    assert response.status_code == 200
    assert body["provider"] == "deterministic_fallback"
    assert body["transaction_id"] == "TXN0001"
    assert body["final_status"] == "DATE_MISMATCH"
    assert body["recommended_action"]
    assert "ground_truth" not in response.text


def test_investigation_missing_transaction():
    response = client.post("/transactions/DOES_NOT_EXIST/investigate")
    assert response.status_code == 404