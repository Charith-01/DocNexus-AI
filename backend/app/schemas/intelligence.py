"""Pydantic contracts for Document Intelligence analysis and API results."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PDFMetadata(BaseModel):
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    keywords: str | None = None
    creator: str | None = None
    producer: str | None = None
    creation_date: str | None = None
    modification_date: str | None = None


class IntelligenceEntity(BaseModel):
    text: str
    label: str
    page: int = Field(ge=1)


class EntityGroups(BaseModel):
    people: list[IntelligenceEntity] = Field(default_factory=list)
    organizations: list[IntelligenceEntity] = Field(default_factory=list)
    locations: list[IntelligenceEntity] = Field(default_factory=list)
    dates: list[IntelligenceEntity] = Field(default_factory=list)
    money: list[IntelligenceEntity] = Field(default_factory=list)
    other: list[IntelligenceEntity] = Field(default_factory=list)


class NLPAnalysis(BaseModel):
    document_type: str
    classification_confidence: float = Field(ge=0, le=1)
    summary: str
    keywords: list[str]
    entities: EntityGroups


class DocumentIntelligenceResult(BaseModel):
    document_id: str
    status: Literal["processed"] = "processed"
    document_type: str
    classification_confidence: float = Field(ge=0, le=1)
    summary: str
    keywords: list[str]
    entities: EntityGroups
    pdf_metadata: PDFMetadata
    page_count: int = Field(ge=0)
    word_count: int = Field(ge=0)
    character_count: int = Field(ge=0)
    is_text_extractable: bool
    requires_ocr: bool
    processed_at: datetime
