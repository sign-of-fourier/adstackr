from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from logging_config import setup_logging
from google_fake.api import router as google_router
from adstackr_fake.api import router as adstackr_router

logger = setup_logging()

app = FastAPI(title="AdStackr Golden Path Architecture Version 2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


google_app = FastAPI(title="Google Fake Stack")
google_app.include_router(google_router, prefix="")

adstackr_app = FastAPI(title="AdStackr Fake")
adstackr_app.include_router(adstackr_router, prefix="")


app.mount("/google", google_app)
app.mount("/adstackr", adstackr_app)


@app.get("/")
async def root():
    return {"message": "AdStackr Golden Path Architecture Version 2"}
