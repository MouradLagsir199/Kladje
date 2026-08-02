"""Reading recipes out of the library.

Every query in here filters on `user_id`. There is no shared recipe table — a recipe belongs to
exactly one person, and a group share is a copy. A query without that filter is a data leak, so
the filter lives in the service rather than being left to each caller.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from receptenapp.core.errors import NotFoundError
from receptenapp.db.models import Recipe, RecipeIngredient, RecipeStep

DEFAULT_LIMIT = 100


@dataclass(frozen=True, slots=True)
class RecipeWithChildren:
    """A recipe and its ordered parts.

    The models carry no ORM relationships on purpose — under async SQLAlchemy a lazy load in a
    response serialiser raises at the worst possible moment. Three explicit queries are cheaper to
    reason about than one implicit one.
    """

    recipe: Recipe
    ingredients: list[RecipeIngredient]
    steps: list[RecipeStep]


async def list_recipes(
    db: AsyncSession, user_id: uuid.UUID, *, limit: int = DEFAULT_LIMIT
) -> list[Recipe]:
    result = await db.execute(
        select(Recipe)
        .where(
            Recipe.user_id == user_id,
            Recipe.deleted_at.is_(None),
            Recipe.is_archived.is_(False),
        )
        .order_by(Recipe.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_recipe(
    db: AsyncSession, user_id: uuid.UUID, recipe_id: uuid.UUID
) -> RecipeWithChildren:
    """One recipe with its ingredients and steps, both already in position order.

    Ordered here rather than in the client: position is the recipe's own sequence, and a step list
    that arrives shuffled is not a display bug, it is a wrong recipe.
    """
    result = await db.execute(
        select(Recipe).where(
            Recipe.id == recipe_id,
            Recipe.user_id == user_id,
            Recipe.deleted_at.is_(None),
        )
    )
    recipe = result.scalar_one_or_none()
    if recipe is None:
        # Same answer for "does not exist" and "belongs to someone else". Distinguishing them
        # would confirm that a given recipe id exists, which is not ours to tell.
        raise NotFoundError("Dit recept bestaat niet of is niet van jou.")

    ingredients = await db.execute(
        select(RecipeIngredient)
        .where(RecipeIngredient.recipe_id == recipe_id)
        .order_by(RecipeIngredient.position)
    )
    steps = await db.execute(
        select(RecipeStep).where(RecipeStep.recipe_id == recipe_id).order_by(RecipeStep.position)
    )

    return RecipeWithChildren(
        recipe=recipe,
        ingredients=list(ingredients.scalars().all()),
        steps=list(steps.scalars().all()),
    )
