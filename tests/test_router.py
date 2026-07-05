def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_response_carries_request_id_header(client):
    response = client.get("/health")
    assert "x-request-id" in response.headers


def test_list_document_types(client):
    response = client.get("/api/v1/document-types")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(body["items"])
    assert any(item["document_type"] == "sample" for item in body["items"])


def test_create_document_success(client):
    response = client.post(
        "/api/v1/documents",
        json={"document_type": "sample", "data": {"name": "Grace Hopper"}},
    )

    assert response.status_code == 201
    assert response.headers["location"].endswith(f"/api/v1/documents/{response.json()['document_id']}")
    body = response.json()
    assert body["document_type"] == "sample"
    assert body["output_format"] == "docx"
    assert body["filename"].endswith(".docx")
    assert body["content_url"].endswith(f"/api/v1/documents/{body['document_id']}/content")
    assert body["size_bytes"] > 0
    # The response must never leak the server's internal filesystem layout.
    assert "file_path" not in body
    assert "/app/" not in body["content_url"] and "generated" not in body["content_url"]


def test_create_document_unknown_type_returns_404(client):
    response = client.post(
        "/api/v1/documents",
        json={"document_type": "nope", "data": {}},
    )

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "TEMPLATE_NOT_FOUND"
    assert "request_id" in error


def test_create_document_missing_fields_returns_unified_validation_shape(client):
    response = client.post(
        "/api/v1/documents",
        json={"invoice_number": "INV-1001"},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    field_names = {f["field"] for f in error["fields"]}
    assert {"document_type", "data"} <= field_names


def test_list_documents_includes_created_one(client):
    create_response = client.post(
        "/api/v1/documents", json={"document_type": "sample", "data": {"name": "Ada"}}
    )
    document_id = create_response.json()["document_id"]

    list_response = client.get("/api/v1/documents")

    assert list_response.status_code == 200
    body = list_response.json()
    assert body["count"] == len(body["items"])
    assert any(item["document_id"] == document_id for item in body["items"])


def test_get_document_returns_metadata(client):
    create_response = client.post(
        "/api/v1/documents", json={"document_type": "sample", "data": {"name": "Ada"}}
    )
    document_id = create_response.json()["document_id"]

    response = client.get(f"/api/v1/documents/{document_id}")

    assert response.status_code == 200
    assert response.json()["document_id"] == document_id


def test_get_document_unknown_id_returns_404(client):
    response = client.get(f"/api/v1/documents/{'0' * 32}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_get_document_malformed_id_returns_422(client):
    response = client.get("/api/v1/documents/not-a-valid-id")
    assert response.status_code == 422


def test_create_then_fetch_content_round_trip(client):
    create_response = client.post(
        "/api/v1/documents", json={"document_type": "sample", "data": {"name": "Alan Turing"}}
    )
    content_url = create_response.json()["content_url"]

    content_response = client.get(content_url)

    assert content_response.status_code == 200
    assert content_response.content


def test_delete_document_removes_it(client):
    create_response = client.post(
        "/api/v1/documents", json={"document_type": "sample", "data": {"name": "Ada"}}
    )
    document_id = create_response.json()["document_id"]

    delete_response = client.delete(f"/api/v1/documents/{document_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/documents/{document_id}")
    assert get_response.status_code == 404


def test_delete_unknown_document_returns_404(client):
    response = client.delete(f"/api/v1/documents/{'0' * 32}")
    assert response.status_code == 404


def test_content_of_unknown_document_returns_404(client):
    response = client.get(f"/api/v1/documents/{'0' * 32}/content")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_path_traversal_style_id_is_rejected_before_touching_filesystem(client):
    # The decoded `../..` produces extra path segments that don't match
    # the single-segment {document_id} route at all, so this never even
    # reaches document_id validation — routing itself rejects it.
    response = client.get("/api/v1/documents/..%2F..%2Fetc%2Fpasswd/content")
    assert response.status_code == 404
