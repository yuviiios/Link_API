import asyncio
import json
from pathlib import Path

import httpx
import pytest
from yarl import URL

from app.main import app
from app.services import analysis_service, llm_service
from app.services.website_extractor import Page, UnsafeWebsite, extract_page, validate_destination

request_client = httpx.AsyncClient
example = Path(__file__).resolve().parents[1] / "examples" / "response.json"


def post_link(payload):
    async def request():
        async with request_client(transport=httpx.ASGITransport(app=app), base_url="http://test", trust_env=False) as client:
            return await client.post("/link-analysis", json=payload)

    return asyncio.run(request())


@pytest.mark.parametrize("url", ["http://127.0.0.1/", "http://[::1]/", "https://example.com:8443/"])
def test_blocks_unsafe_destination(url):
    with pytest.raises(UnsafeWebsite):
        validate_destination(URL(url))


def test_extracts_unique_visible_content():
    html = b"""<title>Northstar</title><nav>Menu</nav><main>
    <p>We design responsive websites for local businesses.</p>
    <p>We design responsive websites for local businesses.</p>
    <script>untrusted JavaScript</script></main>"""
    page = extract_page(html, "https://example.com/")
    assert page.title == "Northstar"
    assert page.text == "We design responsive websites for local businesses."


def test_invalid_request():
    assert post_link({"url": "bad"}).status_code == 422


def test_missing_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert post_link({"url": "https://example.com"}).status_code == 503


@pytest.mark.parametrize("scenario,expected_status", [
    ("success", 200),
    ("unsupported_evidence", 200),
    ("unavailable", 503),
    ("invalid_json", 502),
])
def test_link_analysis(monkeypatch, scenario, expected_status):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    sample = json.loads(example.read_text(encoding="utf-8"))
    evidence = sample["analysis"]["top_services"][0]["evidence_excerpt"]

    async def fetch_page(url):
        text = (
            "We provide a range of digital services for retailers."
            if scenario == "unsupported_evidence" else evidence
        )
        return Page(url, "Northstar", "", text)

    def provider(request):
        assert request.headers["x-goog-api-key"] == "test-key"
        payload = json.loads(request.content)
        assert payload["generationConfig"]["responseJsonSchema"]["type"] == "object"
        if scenario == "unavailable":
            return httpx.Response(429)
        content = "invalid" if scenario == "invalid_json" else json.dumps(sample)
        return httpx.Response(200, json={"candidates": [{
            "finishReason": "STOP", "content": {"parts": [{"text": content}]},
        }]})

    async_client = request_client
    monkeypatch.setattr(analysis_service, "fetch_page", fetch_page)
    monkeypatch.setattr(llm_service.httpx, "AsyncClient", lambda **kwargs: request_client(
        transport=httpx.MockTransport(provider), **kwargs
    ))
    response = post_link({"url": "https://example.com"})
    assert response.status_code == expected_status
    if scenario == "success":
        assert response.json() == sample
    if scenario == "unsupported_evidence":
        service = response.json()["analysis"]["top_services"][0]
        assert service["basis"] == "inferred_recommendation"
        assert service["evidence_excerpt"] == ""


def test_unsafe_website_returns_400(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert post_link({"url": "http://127.0.0.1"}).status_code == 400
