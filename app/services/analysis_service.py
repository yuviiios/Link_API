from app.config import gemini_settings
from app.schemas import LinkResponse
from app.services.llm_service import ModelError, generate_analysis
from app.services.website_extractor import fetch_page

PLATFORMS = {"Google", "Facebook", "Instagram", "LinkedIn", "X"}


async def analyze_website(website: str) -> LinkResponse:
    key, model = gemini_settings()
    page = await fetch_page(website)
    result = await generate_analysis(page, key, model)
    queries = result.analysis.target_search_queries
    if len({item.query.casefold() for item in queries}) != 5:
        raise ModelError("The analysis provider returned duplicate search queries.")
    if {platform for item in queries for platform in item.platforms} != PLATFORMS:
        raise ModelError("The analysis provider omitted a search platform.")

    evidence = tuple(" ".join(text.casefold().split()) for text in (
        page.title, page.description, page.text
    ))
    for service in result.analysis.top_services:
        excerpt = " ".join(service.evidence_excerpt.casefold().split())
        if service.basis == "website_content" and (
            len(excerpt) < 8 or not any(excerpt in text for text in evidence)
        ):
            service.basis = "inferred_recommendation"
        if service.basis == "inferred_recommendation":
            service.evidence_excerpt = ""

    return LinkResponse(website=page.url, brand=result.brand, analysis=result.analysis)
