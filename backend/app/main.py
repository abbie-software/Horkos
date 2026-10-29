from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.errors import install_error_handlers
from app.routes import audit, demo, events, jobs, oath, payments, sellers

app = FastAPI(title="Horkos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

install_error_handlers(app)
app.include_router(oath.router)
app.include_router(jobs.router)
app.include_router(sellers.router)
app.include_router(payments.router)
app.include_router(audit.router)
app.include_router(events.router)
app.include_router(demo.router)


@app.get("/health")
def health():
    return {"status": "ok", "paypal_environment": settings.paypal_environment}
