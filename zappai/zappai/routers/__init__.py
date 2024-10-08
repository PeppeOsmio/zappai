from fastapi.routing import APIRouter
from zappai.zappai.routers.crops_router import crops_router
from zappai.zappai.routers.predictions_router import predictions_router
from zappai.zappai.routers.locations_router import locations_router

zappai_router = APIRouter(prefix="")
zappai_router.include_router(crops_router)
zappai_router.include_router(predictions_router)
zappai_router.include_router(locations_router)
