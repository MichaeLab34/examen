"""Pydantic schemas for the prediction API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HealthResponse(BaseModel):
    status: str = "ok"


class ReadyResponse(BaseModel):
    ready: bool
    model_path: str | None = None
    detail: str | None = None


class PredictionRequest(BaseModel):
    """Raw student records as extracted from SI/LMS systems."""

    model_config = ConfigDict(extra="forbid")

    records: list[dict[str, Any]] = Field(..., min_length=1, max_length=500)

    @field_validator("records")
    @classmethod
    def records_must_be_objects(cls, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("Each record must be a JSON object")
        return records


class PredictionItem(BaseModel):
    proba_abandon: float = Field(..., ge=0.0, le=1.0)
    alerte: int = Field(..., ge=0, le=1)


class PredictionResponse(BaseModel):
    predictions: list[PredictionItem]
