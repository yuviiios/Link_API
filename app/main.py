from fastapi import FastAPI, HTTPException

from app.config import ConfigurationError
from app.schemas import LinkRequest, LinkResponse
from app.services.analysis_service import analyze_website
from app.services.llm_service import ModelError, ModelUnavailable
from app.services.website_extractor import UnsafeWebsite, WebsiteError

app = FastAPI(title="Website Link Analysis API", version="1.0.0")


@app.post(
    "/link-analysis",
    response_model=LinkResponse,
    responses={
        400: {"description": "Unsupported or unsafe website URL"},
        502: {"description": "Website fetch failed or model response was invalid"},
        503: {"description": "Analysis provider unavailable"},
    },
)
async def link_analysis(request: LinkRequest) -> LinkResponse:
    try:
        return await analyze_website(str(request.url))
    except UnsafeWebsite as error:
        raise HTTPException(400, str(error)) from error
    except (ConfigurationError, ModelUnavailable) as error:
        raise HTTPException(503, str(error)) from error
    except (WebsiteError, ModelError) as error:
        raise HTTPException(502, str(error)) from error
