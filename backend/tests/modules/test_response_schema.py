from app.shared.responses.base import ApiResponse


def test_api_response_success_wraps_payload() -> None:
    payload = {"session_id": "sess_123"}

    response = ApiResponse.success(payload)

    assert response.code == 0
    assert response.message == "success"
    assert response.data == payload
