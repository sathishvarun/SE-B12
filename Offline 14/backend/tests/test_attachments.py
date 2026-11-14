"""Attachments: upload validation (type/size), storage naming, download, delete, isolation."""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Attachment
from app.services import storage as storage_module
from app.services.attachment_service import sanitize_filename
from app.services.storage import FileTooLargeError, LocalStorage
from tests.conftest import API, Seller, create_contact, create_deal

PDF = ("report.pdf", b"%PDF-1.4 hello", "application/pdf")
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _upload(client: TestClient, seller: Seller, file=PDF, **form: int) -> "object":
    return client.post(
        f"{API}/attachments",
        files={"file": file},
        data={k: str(v) for k, v in form.items()},
        headers=seller.headers,
    )


@pytest.fixture
def contact(client: TestClient, seller_a: Seller) -> dict:
    return create_contact(client, seller_a)


def _upload_root() -> Path:
    return Path(settings.UPLOAD_DIR).resolve()


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


def test_upload_to_contact_stores_under_generated_name(
    client: TestClient, db: Session, seller_a: Seller, contact: dict
) -> None:
    resp = _upload(client, seller_a, contact_id=contact["id"])
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert set(body) == {
        "id",
        "filename",
        "content_type",
        "size_bytes",
        "contact_id",
        "deal_id",
        "created_at",
    }
    assert body["filename"] == "report.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size_bytes"] == len(PDF[1])
    assert body["contact_id"] == contact["id"] and body["deal_id"] is None

    row = db.get(Attachment, body["id"])
    assert row is not None
    assert "report" not in row.storage_path  # never the user-supplied name
    assert row.storage_path.startswith(f"{seller_a.id}/") and row.storage_path.endswith(".pdf")
    stored = _upload_root() / row.storage_path
    assert stored.read_bytes() == PDF[1]

    # visible on the contact detail
    detail = client.get(f"{API}/contacts/{contact['id']}", headers=seller_a.headers).json()
    assert [a["id"] for a in detail["attachments"]] == [body["id"]]


def test_upload_to_deal(client: TestClient, seller_a: Seller, contact: dict) -> None:
    deal = create_deal(client, seller_a, contact["id"])
    resp = _upload(
        client, seller_a, file=("pic.PNG", b"\x89PNG data", "image/png"), deal_id=deal["id"]
    )
    assert resp.status_code == 201
    assert resp.json()["deal_id"] == deal["id"]
    detail = client.get(f"{API}/deals/{deal['id']}", headers=seller_a.headers).json()
    assert len(detail["attachments"]) == 1


@pytest.mark.parametrize(
    "file",
    [
        ("a.pdf", b"x", "application/pdf"),
        ("a.png", b"x", "image/png"),
        ("a.jpg", b"x", "image/jpeg"),
        ("a.jpeg", b"x", "image/jpg"),
        ("a.docx", b"x", DOCX_TYPE),
        ("a.xlsx", b"x", XLSX_TYPE),
    ],
)
def test_allowed_types(client: TestClient, seller_a: Seller, contact: dict, file) -> None:
    assert _upload(client, seller_a, file=file, contact_id=contact["id"]).status_code == 201


@pytest.mark.parametrize(
    "file",
    [
        ("evil.exe", b"MZ", "application/octet-stream"),
        ("notes.txt", b"hi", "text/plain"),
        ("page.html", b"<h1>", "text/html"),
        ("noext", b"x", "application/pdf"),
        ("fake.pdf", b"x", "text/html"),  # content type doesn't match extension
        ("a.pdf.exe", b"x", "application/pdf"),
    ],
)
def test_disallowed_types_400(client: TestClient, seller_a: Seller, contact: dict, file) -> None:
    resp = _upload(client, seller_a, file=file, contact_id=contact["id"])
    assert resp.status_code == 400
    assert list(_upload_root().rglob("*.*")) == [] if _upload_root().exists() else True


def test_empty_file_400(client: TestClient, seller_a: Seller, contact: dict) -> None:
    resp = _upload(
        client, seller_a, file=("e.pdf", b"", "application/pdf"), contact_id=contact["id"]
    )
    assert resp.status_code == 400
    assert not any(p.is_file() for p in _upload_root().rglob("*"))


def test_file_over_10mb_is_413(client: TestClient, seller_a: Seller, contact: dict) -> None:
    assert settings.MAX_UPLOAD_MB == 10
    big = b"0" * (10 * 1024 * 1024 + 1)
    resp = _upload(
        client, seller_a, file=("big.pdf", big, "application/pdf"), contact_id=contact["id"]
    )
    assert resp.status_code == 413
    assert not any(p.is_file() for p in _upload_root().rglob("*"))


def test_file_exactly_10mb_is_ok(client: TestClient, seller_a: Seller, contact: dict) -> None:
    data = b"0" * (10 * 1024 * 1024)
    resp = _upload(
        client, seller_a, file=("ok.pdf", data, "application/pdf"), contact_id=contact["id"]
    )
    assert resp.status_code == 201
    assert resp.json()["size_bytes"] == len(data)


def test_streaming_limit_enforced_when_size_unknown(tmp_path: Path) -> None:
    """LocalStorage.save enforces max_bytes on the stream itself and removes the partial file."""
    store = LocalStorage(str(tmp_path))
    with pytest.raises(FileTooLargeError):
        store.save(1, io.BytesIO(b"x" * 20), "pdf", max_bytes=10)
    assert not any(p.is_file() for p in tmp_path.rglob("*"))


@pytest.mark.parametrize("form", [{}, {"contact_id": 1, "deal_id": 1}])
def test_requires_exactly_one_parent_400(
    client: TestClient, seller_a: Seller, contact: dict, form: dict
) -> None:
    if "deal_id" in form:
        deal = create_deal(client, seller_a, contact["id"])
        form = {"contact_id": contact["id"], "deal_id": deal["id"]}
    assert _upload(client, seller_a, **form).status_code == 400


def test_upload_to_missing_parent_404(client: TestClient, seller_a: Seller) -> None:
    assert _upload(client, seller_a, contact_id=999).status_code == 404
    assert _upload(client, seller_a, deal_id=999).status_code == 404


def test_sanitize_filename() -> None:
    assert sanitize_filename("../../etc/passwd.pdf", "pdf") == "passwd.pdf"
    assert sanitize_filename("C:\\Users\\x\\my file.pdf", "pdf") == "my file.pdf"
    assert sanitize_filename("<script>.pdf", "pdf") == "_script_.pdf"
    assert sanitize_filename(None, "png") == "file.png"
    assert sanitize_filename("...", "png") == "file.png"
    long = sanitize_filename("a" * 300 + ".pdf", "pdf")
    assert len(long) <= 255 and long.endswith(".pdf")


def test_path_traversal_rejected_by_storage(tmp_path: Path) -> None:
    store = LocalStorage(str(tmp_path))
    from app.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        store.open("../outside.pdf")
    with pytest.raises(NotFoundError):
        store.open("1/missing.pdf")
    store.delete("../outside.pdf")  # logged and ignored, never raises


def test_get_storage_returns_module_singleton() -> None:
    assert storage_module.get_storage() is storage_module.storage


# ---------------------------------------------------------------------------
# Download / delete
# ---------------------------------------------------------------------------


def test_download(client: TestClient, seller_a: Seller, contact: dict) -> None:
    att = _upload(client, seller_a, contact_id=contact["id"]).json()
    resp = client.get(f"{API}/attachments/{att['id']}", headers=seller_a.headers)
    assert resp.status_code == 200
    assert resp.content == PDF[1]
    assert resp.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="report.pdf"' in resp.headers["content-disposition"]


def test_download_when_file_missing_on_disk_404(
    client: TestClient, db: Session, seller_a: Seller, contact: dict
) -> None:
    att = _upload(client, seller_a, contact_id=contact["id"]).json()
    row = db.get(Attachment, att["id"])
    assert row is not None
    (_upload_root() / row.storage_path).unlink()
    assert client.get(f"{API}/attachments/{att['id']}", headers=seller_a.headers).status_code == 404


def test_delete_removes_row_and_file(
    client: TestClient, db: Session, seller_a: Seller, contact: dict
) -> None:
    att = _upload(client, seller_a, contact_id=contact["id"]).json()
    row = db.get(Attachment, att["id"])
    assert row is not None
    path = _upload_root() / row.storage_path
    assert path.exists()
    resp = client.delete(f"{API}/attachments/{att['id']}", headers=seller_a.headers)
    assert resp.status_code == 204
    assert not path.exists()
    db.expire_all()
    assert db.get(Attachment, att["id"]) is None
    assert client.get(f"{API}/attachments/{att['id']}", headers=seller_a.headers).status_code == 404


def test_deleting_contact_removes_attachment_files(
    client: TestClient, db: Session, seller_a: Seller, contact: dict
) -> None:
    att = _upload(client, seller_a, contact_id=contact["id"]).json()
    row = db.get(Attachment, att["id"])
    assert row is not None
    path = _upload_root() / row.storage_path
    client.delete(f"{API}/contacts/{contact['id']}", headers=seller_a.headers)
    assert not path.exists()


def test_deleting_deal_removes_attachment_files(
    client: TestClient, db: Session, seller_a: Seller, contact: dict
) -> None:
    deal = create_deal(client, seller_a, contact["id"])
    att = _upload(client, seller_a, deal_id=deal["id"]).json()
    row = db.get(Attachment, att["id"])
    assert row is not None
    path = _upload_root() / row.storage_path
    assert path.exists()
    client.delete(f"{API}/deals/{deal['id']}", headers=seller_a.headers)
    assert not path.exists()


def test_oversized_request_body_rejected_by_middleware_413(
    client: TestClient, seller_a: Seller, contact: dict
) -> None:
    """Bodies over (MAX_UPLOAD_MB + 1) MB are refused before FastAPI parses them."""
    big = b"0" * ((settings.MAX_UPLOAD_MB + 1) * 1024 * 1024 + 10)
    resp = _upload(
        client, seller_a, file=("huge.pdf", big, "application/pdf"), contact_id=contact["id"]
    )
    assert resp.status_code == 413
    assert resp.json() == {"detail": "Request body too large"}
    assert not any(p.is_file() for p in _upload_root().rglob("*"))


def test_middleware_counts_streamed_bodies() -> None:
    """Chunked bodies without Content-Length are counted as they arrive."""
    import asyncio

    from app.middleware import MaxBodySizeMiddleware

    async def inner_app(scope, receive, send) -> None:  # reads the whole body
        while True:
            message = await receive()
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def run(chunks: list[bytes]) -> int:
        queue = [
            {"type": "http.request", "body": c, "more_body": i < len(chunks) - 1}
            for i, c in enumerate(chunks)
        ]
        sent: list[dict] = []

        async def receive() -> dict:
            return queue.pop(0)

        async def send(message: dict) -> None:
            sent.append(message)

        mw = MaxBodySizeMiddleware(inner_app, max_bytes=10)
        await mw({"type": "http", "headers": []}, receive, send)
        return sent[0]["status"]

    assert asyncio.run(run([b"12345", b"12345"])) == 200
    assert asyncio.run(run([b"123456", b"123456"])) == 413

    async def lifespan_passthrough() -> bool:
        called = []

        async def app(scope, receive, send) -> None:
            called.append(scope["type"])

        await MaxBodySizeMiddleware(app, 1)({"type": "lifespan"}, None, None)
        return called == ["lifespan"]

    assert asyncio.run(lifespan_passthrough())


def test_attachments_require_auth(client: TestClient) -> None:
    assert client.get(f"{API}/attachments/1").status_code == 401
    assert client.delete(f"{API}/attachments/1").status_code == 401


# ---------------------------------------------------------------------------
# Cross-seller isolation
# ---------------------------------------------------------------------------


def test_cross_seller_attachment_access_is_404(
    client: TestClient, db: Session, seller_a: Seller, seller_b: Seller, contact: dict
) -> None:
    att = _upload(client, seller_a, contact_id=contact["id"]).json()
    url = f"{API}/attachments/{att['id']}"
    assert client.get(url, headers=seller_b.headers).status_code == 404
    assert client.delete(url, headers=seller_b.headers).status_code == 404
    # still there for A
    assert client.get(url, headers=seller_a.headers).status_code == 200


def test_cannot_upload_to_other_sellers_contact_or_deal(
    client: TestClient, seller_a: Seller, seller_b: Seller, contact: dict
) -> None:
    deal = create_deal(client, seller_a, contact["id"])
    assert _upload(client, seller_b, contact_id=contact["id"]).status_code == 404
    assert _upload(client, seller_b, deal_id=deal["id"]).status_code == 404
