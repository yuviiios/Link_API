from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Platform = Literal["Google", "Facebook", "Instagram", "LinkedIn", "X"]


class LinkRequest(BaseModel):
    url: HttpUrl


class Brand(BaseModel):
    name: Text
    category: Text
    summary: Text


class Competitor(BaseModel):
    name: Text
    focus: Text
    relevance: Text
    potential_strengths: list[Text]
    potential_gaps: list[Text]
    evidence_status: Literal["unverified_model_suggestion"]


class CompetitorAnalysis(BaseModel):
    brand_overview: Text
    products_and_services: list[Text]
    competitors: list[Competitor]
    strengths: list[Text]
    opportunities: list[Text]


class SearchQuery(BaseModel):
    query: Text
    platforms: list[Platform] = Field(min_length=1)
    intent: Text
    business_relevance: Text
    target_audience: Text


class SeoImprovements(BaseModel):
    primary_keyword: Text
    secondary_keywords: list[Text]
    long_tail_keywords: list[Text]
    business_keywords: list[Text]
    recommended_title: Text
    title_rationale: Text
    meta_description: Text
    supporting_content: list[Text]


class Service(BaseModel):
    name: Text
    description: Text
    target_industry: Text
    target_customer: Text
    main_benefit: Text
    basis: Literal["website_content", "inferred_recommendation"]
    evidence_excerpt: str


class TargetAudience(BaseModel):
    primary_audience: list[Text]
    secondary_audience: list[Text]
    industries: list[Text]
    business_types: list[Text]
    customer_profiles: list[Text]
    geographical_focus: list[Text]
    customer_needs: list[Text]
    interests: list[Text]
    marketing_segments: list[Text]


class Analysis(BaseModel):
    competitor_analysis: CompetitorAnalysis
    target_search_queries: list[SearchQuery] = Field(min_length=5, max_length=5)
    seo_improvements: SeoImprovements
    top_services: list[Service] = Field(max_length=5)
    target_audience: TargetAudience


class ModelResult(BaseModel):
    brand: Brand
    analysis: Analysis


class LinkResponse(ModelResult):
    success: Literal[True] = True
    website: HttpUrl
