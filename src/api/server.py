from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from src.api.db_helpers import map_integrity_error
from src.api.routers import auth, cookbook, feed, recipes, reviews, social, users
from src.api.schemas import HealthResponse

app = FastAPI(title="JobWise - Recipe Rating API")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(feed.router, prefix="/api/v1")
app.include_router(recipes.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(cookbook.router, prefix="/api/v1")
app.include_router(social.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


@app.exception_handler(IntegrityError)
async def handle_integrity_error(_request: Request, exc: IntegrityError) -> JSONResponse:
    http_exc = map_integrity_error(exc)
    return JSONResponse(status_code=http_exc.status_code, content={"detail": http_exc.detail})


@app.get("/", response_model=HealthResponse)
def root() -> HealthResponse:
    return HealthResponse(status="ok", docs="/docs")
