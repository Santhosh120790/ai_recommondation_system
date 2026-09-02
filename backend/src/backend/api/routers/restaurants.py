from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.llm import get_chat_model
from backend.data_pipeline import repository
from backend.data_pipeline.schemas import Restaurant

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


class PreviewRequest(BaseModel):
    raw_text: str


class UpdateRequest(BaseModel):
    updates: dict


@router.get("")
def list_restaurants() -> list[Restaurant]:
    return repository.load_restaurants()


@router.get("/{item_id}")
def get_restaurant(item_id: int) -> Restaurant:
    try:
        return repository.get_restaurant(item_id)
    except repository.RestaurantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/preview")
def preview_restaurant(request: PreviewRequest) -> Restaurant:
    """Structure a raw description via the LLM pipeline without saving it, so the
    frontend can show a confirm/edit step before the write actually happens."""
    llm = get_chat_model(temperature=0)
    return repository.structure_new_restaurant(llm, request.raw_text)


@router.post("", status_code=201)
def save_restaurant(restaurant: Restaurant) -> Restaurant:
    """Save an already-structured (and possibly user-edited) restaurant returned
    from /preview. The frontend's confirm step is the human-in-the-loop gate,
    so this saves directly."""
    return repository.save_new_restaurant(restaurant, confirm=True)


@router.patch("/{item_id}")
def update_restaurant(item_id: int, request: UpdateRequest) -> Restaurant:
    try:
        return repository.update_restaurant(item_id, request.updates, confirm=True)
    except repository.RestaurantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{item_id}", status_code=204)
def delete_restaurant(item_id: int) -> None:
    try:
        repository.delete_restaurant(item_id, confirm=True)
    except repository.RestaurantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
