def test_register_file_too_large(client):
    with open("tests/fixtures/large_image.jpg", "rb") as f:
        resp = client.post(
            "/api/register",
            files={"file": ("large_image.jpg", f, "image/jpeg")},
            data={"name": "BigFile"},
        )
    assert resp.status_code == 413
    assert resp.json()["detail"] == "File too large. Max 5MB allowed."


def test_register_dimensions_too_large(client):
    from PIL import Image
    import io

    img = Image.new("RGB", (3000, 2000), (100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    buf.seek(0)

    resp = client.post(
        "/api/register",
        files={"file": ("big_dim.jpg", buf, "image/jpeg")},
        data={"name": "BigDim"},
    )
    assert resp.status_code == 413
    assert "Image dimensions too large" in resp.json()["detail"]
