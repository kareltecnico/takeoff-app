from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class ProjectCreateRequest(BaseModel):
    project_code: str
    project_name: str
    contractor_name: str | None = None
    foreman_name: str | None = None


class PlanInputPayload(BaseModel):
    stories: int = Field(ge=0)
    kitchens: int = Field(ge=0)
    garbage_disposals: int = Field(ge=0)
    laundry_rooms: int = Field(ge=0)
    lav_faucets: int = Field(ge=0)
    toilets: int = Field(ge=0)
    showers: int = Field(ge=0)
    bathtubs: int = Field(ge=0)
    half_baths: int = Field(ge=0)
    double_bowl_vanities: int = Field(ge=0)
    hose_bibbs: int = Field(ge=0)
    ice_makers: int = Field(ge=0)
    water_heater_tank_qty: int = Field(ge=0)
    water_heater_tankless_qty: int = Field(ge=0)
    sewer_distance_lf: Decimal = Field(ge=0)
    water_distance_lf: Decimal = Field(ge=0)


class GenerateTakeoffRequest(BaseModel):
    project_code: str
    template_code: str
    tax_rate_override: Decimal | None = None
    plan: PlanInputPayload


class UpdateLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    qty: Decimal | None = Field(default=None, gt=0)
    stage: str | None = None
    factor: Decimal | None = Field(default=None, gt=0)
    sort_order: int | None = Field(default=None, ge=0)


class ExportRequest(BaseModel):
    format: str
