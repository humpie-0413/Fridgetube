from fastapi import APIRouter

from api.channels import router as channels_router
from api.ingredients import router as ingredients_router
from api.recipe import router as recipe_router
from api.search import router as search_router
from api.user_ingredients import router as user_ingredients_router

router = APIRouter()
router.include_router(search_router)
router.include_router(ingredients_router)
router.include_router(recipe_router)
router.include_router(channels_router)
router.include_router(user_ingredients_router)
