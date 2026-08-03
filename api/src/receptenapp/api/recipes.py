import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from receptenapp.core.security import get_current_user
from receptenapp.db.models import User
from receptenapp.db.session import get_db
from receptenapp.schemas.recipe import (
    IngredientOut,
    RecipeDetail,
    RecipeList,
    RecipeSummary,
    StepOut,
)
from receptenapp.services import recipes as recipes_service

router = APIRouter(prefix="/v1/recipes", tags=["recipes"])


@router.get("")
async def list_recipes(
    limit: int = Query(default=recipes_service.DEFAULT_LIMIT, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecipeList:
    rows = await recipes_service.list_recipes(db, user.id, limit=limit)
    # No cursor yet: the library screen loads the whole list and the free tier caps imports at 10.
    # Pagination arrives with the first user who has enough recipes to need it.
    return RecipeList(items=[RecipeSummary.model_validate(row) for row in rows])


def to_detail(found: recipes_service.RecipeWithChildren) -> RecipeDetail:
    """Shared with the import save endpoint, which returns a finished recipe too."""
    return RecipeDetail(
        **RecipeSummary.model_validate(found.recipe).model_dump(),
        description=found.recipe.description,
        kcal_per_serving=found.recipe.kcal_per_serving,
        source_url=found.recipe.source_url,
        source_title=found.recipe.source_title,
        notes=found.recipe.notes,
        last_cooked_at=found.recipe.last_cooked_at,
        field_provenance=found.recipe.field_provenance,
        ingredients=[IngredientOut.model_validate(row) for row in found.ingredients],
        steps=[StepOut.model_validate(row) for row in found.steps],
    )


@router.get("/{recipe_id}")
async def get_recipe(
    recipe_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecipeDetail:
    return to_detail(await recipes_service.get_recipe(db, user.id, recipe_id))
