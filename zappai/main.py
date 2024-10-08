from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware
from zappai import logging_conf
from zappai.database.di import get_session_maker
from zappai.zappai.di import get_location_repository

logging_conf.create_logger(config=logging_conf.get_default_conf())

import logging
import traceback
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from zappai.users.routers import user_router
from zappai.auth_tokens.routers import auth_token_router
from zappai.zappai.routers import zappai_router


@asynccontextmanager
async def lifespan(
    app: FastAPI
):
    session_maker = get_session_maker()
    location_repository = get_location_repository()
    async with session_maker() as session:
        await location_repository.set_locations_to_not_downloading(session=session)
        await session.commit()
    logging.info("Done")
    yield


app = FastAPI(
    title="ZappAI",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)


# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(user_router, prefix="/api", tags=["User"])
app.include_router(auth_token_router, prefix="/api", tags=["Auth"])
app.include_router(zappai_router, prefix="/api", tags=["Zappai"])


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logging.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"type": type(exc).__qualname__, "detail": str(exc)},
    )
