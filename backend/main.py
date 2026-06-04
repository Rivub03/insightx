from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.modules.datasources.router import router as datasources_router

# Auto-generate database tables using SQLAlchemy (Alembic should be used in production)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="InsightX Backend API",
    description="Agentic Reporting Platform Engine",
    version="1.0.0"
)

# Configure CORS so your Next.js frontend running on port 3000 can talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Domain Routers
app.include_router(datasources_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "operational"}