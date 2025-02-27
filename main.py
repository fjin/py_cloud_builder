from fastapi import FastAPI
from routes import users, items, environments, resources, build, unbuild
from database import Base, engine

app = FastAPI(title="My API Server", version="1.0")

# Create database tables
Base.metadata.create_all(bind=engine)

# Include API routes
app.include_router(users.router, prefix="/users", tags=["Users"])

app.include_router(items.router, prefix="/items", tags=["Items"])

app.include_router(environments.router, prefix="/environments", tags=["Environments"])

app.include_router(resources.router, prefix="/resources", tags=["Resources"])

app.include_router(build.router, prefix="/build", tags=["Build"])

app.include_router(unbuild.router, prefix="/unbuild", tags=["unbuild"])

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the API!"}
