from fastapi import FastAPI
from routes import environment, resources, build, unbuild, status
from database import Base, engine
import logging

logging.basicConfig(
    level=logging.DEBUG,  # Set the minimum level to DEBUG; change to INFO or ERROR as needed.
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

app = FastAPI(title="PY_Builder API Server", version="1.0")

# Create database tables
Base.metadata.create_all(bind=engine)

# Include API routes
app.include_router(environment.router, prefix="/environment", tags=["Environment"])

app.include_router(resources.router, prefix="/resources", tags=["Resources"])

app.include_router(build.router, prefix="/build", tags=["Build"])

app.include_router(unbuild.router, prefix="/unbuild", tags=["unbuild"])

app.include_router(status.router, prefix="/status", tags=["status"])


# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the API!"}
