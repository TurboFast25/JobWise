from fastapi import FastAPI
from src.api.routers import feed, recipes, reviews, cookbook, social, users

app = FastAPI(title="JobWise - Recipe Rating API")

app.include_router(feed.router, prefix="/api/v1")
app.include_router(recipes.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(cookbook.router, prefix="/api/v1")
app.include_router(social.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}
