from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ..accounts import tiers
from ..calc import settings as calc_settings
from ..calc.compare import compare, variant_row
from ..scheme.editor import EditError
from ..scheme.model import Scheme
from .session import Signed, site

router = APIRouter(prefix="/api/projects", tags=["Проекты"])


class NewProject(BaseModel):
    name: str = Field(max_length=120)
    scheme: Scheme | None = None


class SaveScheme(BaseModel):
    scheme: Scheme
    variant: int | None = None


class ProjectChange(BaseModel):
    name: str | None = Field(None, max_length=120)
    archived: bool | None = None


class NewVariant(BaseModel):
    name: str = Field(max_length=120)
    source: int | None = None


class VariantChange(BaseModel):
    name: str = Field(max_length=120)


class ShareRequest(BaseModel):
    team: int


Values = dict[str, float | bool | list[float]]


class SettingsBody(BaseModel):
    settings: Values


class ScenarioBody(BaseModel):
    name: str = Field(max_length=120)
    settings: Values = Field(default_factory=dict)
    period: int = 2
    min_load: bool = True


@router.get("")
def listing(user: Signed, request: Request, archived: bool = False) -> list[dict]:
    return site(request).projects.listing(user, archived)


@router.post("")
def create(user: Signed, data: NewProject, request: Request) -> dict:
    return site(request).projects.create(user, data.name, data.scheme)


@router.get("/{project_id}")
def card(user: Signed, project_id: int, request: Request) -> dict:
    return site(request).projects.get(user, project_id)


@router.get("/{project_id}/scheme")
def scheme(user: Signed, project_id: int, request: Request, variant: int | None = None) -> dict:
    return site(request).projects.scheme(user, project_id, variant)


@router.put("/{project_id}/scheme")
def save(user: Signed, project_id: int, data: SaveScheme, request: Request) -> dict:
    return site(request).projects.save(user, project_id, data.scheme, data.variant)


@router.patch("/{project_id}")
def change(user: Signed, project_id: int, data: ProjectChange, request: Request) -> dict:
    projects = site(request).projects
    result = projects.get(user, project_id)
    if data.name is not None:
        result = projects.rename(user, project_id, data.name)
    if data.archived is not None:
        result = projects.archive(user, project_id, data.archived)
    return result


@router.delete("/{project_id}")
def delete(user: Signed, project_id: int, request: Request) -> dict:
    site(request).projects.delete(user, project_id)
    return {"ok": True}


@router.post("/{project_id}/variants")
def add_variant(user: Signed, project_id: int, data: NewVariant, request: Request) -> dict:
    return site(request).projects.add_variant(user, project_id, data.name, data.source)


@router.patch("/{project_id}/variants/{variant_id}")
def rename_variant(user: Signed, project_id: int, variant_id: int, data: VariantChange, request: Request) -> dict:
    return site(request).projects.rename_variant(user, project_id, variant_id, data.name)


@router.delete("/{project_id}/variants/{variant_id}")
def delete_variant(user: Signed, project_id: int, variant_id: int, request: Request) -> dict:
    return site(request).projects.delete_variant(user, project_id, variant_id)


@router.get("/{project_id}/shares")
def shares(user: Signed, project_id: int, request: Request) -> dict:
    return site(request).collab.shares(user, project_id)


@router.post("/{project_id}/shares")
def share(user: Signed, project_id: int, data: ShareRequest, request: Request) -> dict:
    return site(request).collab.share(user, project_id, data.team)


@router.delete("/{project_id}/shares/{team_id}")
def unshare(user: Signed, project_id: int, team_id: int, request: Request) -> dict:
    return site(request).collab.unshare(user, project_id, team_id)


@router.get("/{project_id}/settings")
def settings(user: Signed, project_id: int, request: Request) -> dict:
    return {"settings": site(request).projects.settings(user, project_id)}


@router.put("/{project_id}/settings")
def save_settings(user: Signed, project_id: int, data: SettingsBody, request: Request) -> dict:
    return {"settings": site(request).projects.save_settings(user, project_id, data.settings)}


@router.get("/{project_id}/scenarios")
def scenarios(user: Signed, project_id: int, request: Request) -> list[dict]:
    return site(request).projects.scenarios(user, project_id)


@router.post("/{project_id}/scenarios")
def add_scenario(user: Signed, project_id: int, data: ScenarioBody, request: Request) -> list[dict]:
    return site(request).projects.add_scenario(user, project_id, data.name, data.settings, data.period, data.min_load)


@router.patch("/{project_id}/scenarios/{scenario_id}")
def update_scenario(user: Signed, project_id: int, scenario_id: int, data: ScenarioBody,
                    request: Request) -> list[dict]:
    return site(request).projects.update_scenario(user, project_id, scenario_id, data.name, data.settings,
                                                  data.period, data.min_load)


@router.delete("/{project_id}/scenarios/{scenario_id}")
def delete_scenario(user: Signed, project_id: int, scenario_id: int, request: Request) -> list[dict]:
    return site(request).projects.delete_scenario(user, project_id, scenario_id)


class CompareBody(BaseModel):
    variants: list[int] = Field(min_length=2, max_length=30)
    settings: Values | None = None
    period: int = Field(2, ge=0, le=2)
    min_load: bool = True


@router.post("/{project_id}/compare")
def compare_variants(user: Signed, project_id: int, data: CompareBody, request: Request) -> dict:
    current = site(request)
    tier = tiers.effective(user)
    if len(data.variants) > tier.compared:
        raise EditError(f"В тарифе «{tier.title}» сравниваются не больше {tier.compared} вариантов")
    project = current.projects.get(user, project_id)
    settings = calc_settings.build(current.reference.values(), project["settings"], data.settings)
    price = current.options.energy_price() if "annual_losses" in tier.features else None
    names = {variant["id"]: variant["name"] for variant in project["variants"]}
    rows = []
    for variant_id in data.variants:
        found = current.projects.scheme(user, project_id, variant_id)
        name = names.get(variant_id, str(variant_id))
        if found["scheme"] is None:
            rows.append({"name": name, "variant": variant_id, "error": "В варианте нет схемы"})
            continue
        scheme = Scheme.model_validate(found["scheme"])
        tiers.check_size(user, len(scheme.poles), len(scheme.consumers))
        rows.append({**variant_row(name, scheme, settings, data.period, data.min_load, price), "variant": variant_id})
    return compare(rows)
