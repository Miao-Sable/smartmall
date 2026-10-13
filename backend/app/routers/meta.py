"""基础字典：过敏源 / 饮食偏好 / 场景模板"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models.user import Allergen, DietPreference
from app.schemas.meta import AllergenOut, DietOut, ScenarioOut
from app.services.mock_data import load_scenario_templates

router = APIRouter()


@router.get("/allergens", response_model=list[AllergenOut])
def list_allergens(session: Session = Depends(get_session)) -> list[Allergen]:
    return session.exec(select(Allergen).order_by(Allergen.id)).all()


@router.get("/diet-preferences", response_model=list[DietOut])
def list_diet_preferences(session: Session = Depends(get_session)) -> list[DietPreference]:
    return session.exec(select(DietPreference).order_by(DietPreference.id)).all()


@router.get("/scenarios", response_model=list[ScenarioOut])
def list_scenarios(session: Session = Depends(get_session)) -> list[ScenarioOut]:
    """场景模板：把模板中的过敏源/偏好名称解析为字典 id，便于前端一键建档案。"""
    allergen_id_by_name = {a.name: a.id for a in session.exec(select(Allergen)).all()}
    diet_id_by_name = {d.name: d.id for d in session.exec(select(DietPreference)).all()}

    result: list[ScenarioOut] = []
    for t in load_scenario_templates():
        result.append(
            ScenarioOut(
                key=t["key"],
                name=t["name"],
                emoji=t.get("emoji", ""),
                description=t.get("description", ""),
                allergen_ids=[
                    allergen_id_by_name[n] for n in t.get("allergen_names", []) if n in allergen_id_by_name
                ],
                diet_ids=[diet_id_by_name[n] for n in t.get("diet_names", []) if n in diet_id_by_name],
            )
        )
    return result
