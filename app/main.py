from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.subjects import router as subjects_router
from app.api.concepts import router as concepts_router
from app.api.packages import router as packages_router
from app.api.questions import router as questions_router
from app.api.assessments import router as assessments_router
from app.api.results import router as results_router
from app.api.validation import router as validation_router
from app.api.tags import router as tags_router
from app.models.sqlmodel import SQLModel, Subject, Concept, ConceptRelation, PackageVersion, Question, Attempt, ValidationIssue, Tag, FlashcardTag

app = FastAPI(
    title="Knowledge Graph Learning Studio API",
    description="Local-first knowledge graph and assessment platform API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://43.157.212.74:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(subjects_router)
app.include_router(concepts_router)
app.include_router(packages_router)
app.include_router(questions_router)
app.include_router(assessments_router)
app.include_router(results_router)
app.include_router(validation_router)
app.include_router(tags_router)


@app.on_event("startup")
async def on_startup():
    from app.db import engine
    SQLModel.metadata.create_all(bind=engine)


@app.get("/")
async def root():
    return {"message": "Knowledge Graph Learning Studio API", "version": "0.1.0"}
