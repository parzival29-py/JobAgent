from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
from pypdf import PdfReader
from docx import Document

import shutil
import json

from backend.profile import build_profile

from backend.ai import (
    ask_gemini,
    analyze_resume,
    match_job,
    analyze_job_description,
    calculate_ats_score,
    optimize_until_80,
    optimize_until_90,
)

from backend.jobs import (
    get_all_jobs,
    filter_jobs,
)

from backend.applications import (
    create_application,
    get_applications,
    get_application,
    update_application,
    update_application_status,
    delete_application,
    get_application_stats,
)

from backend.application_ai import (
    generate_cover_letter,
    analyze_application_question,
    generate_application_answer,
    generate_application_answers,
)

from backend.resume_generator import (
    generate_resume_docx,
    generate_tailored_resume,
)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="Aryaman's Job Application Agent",
    description="Personal AI-powered job application assistant",
    version="1.0.0",
)

# Enable CORS for local and web browser dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DIRECTORIES
# ============================================================

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

OPTIMIZED_DIR = UPLOAD_DIR / "optimized"
OPTIMIZED_DIR.mkdir(exist_ok=True)

PROFILE_FILE = UPLOAD_DIR / "resume_profile.json"
PREFERENCES_FILE = UPLOAD_DIR / "job_preferences.json"


# ============================================================
# REQUEST MODELS
# ============================================================

class JobPreferences(BaseModel):
    opportunity_type: str = "internship"
    work_mode: str = "remote"
    domains: list[str] = Field(default_factory=list)
    location: str = "Anywhere"
    minimum_stipend: int = 0
    experience_level: str = "Fresher"


class ATSRequest(BaseModel):
    job_description: str


class ResumeOptimizeRequest(BaseModel):
    job_description: str
    max_iterations: int = 8


class ApplicationCreateRequest(BaseModel):
    company: str
    job_title: str
    job_url: str = ""
    job_description: str = ""
    ats_score: float | None = None
    resume_version: str = ""
    cover_letter: str = ""
    status: str = "Saved"
    notes: str = ""


class ApplicationUpdateRequest(BaseModel):
    company: str | None = None
    job_title: str | None = None
    job_url: str | None = None
    job_description: str | None = None
    ats_score: float | None = None
    resume_version: str | None = None
    cover_letter: str | None = None
    status: str | None = None
    notes: str | None = None


class ApplicationStatusRequest(BaseModel):
    status: str


class CoverLetterRequest(BaseModel):
    job_description: str
    company: str = ""
    job_title: str = ""


class ApplicationQuestionRequest(BaseModel):
    question: str
    job_description: str = ""


class ApplicationQuestionsRequest(BaseModel):
    questions: list[str]
    job_description: str = ""


class WorkflowE2ERequest(BaseModel):
    job_description: str
    company: str = "Apex Cloud Systems"
    job_title: str = "Software Engineering Intern"
    save_application: bool = True


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def load_current_profile():
    if not PROFILE_FILE.exists():
        return None
    try:
        profile_data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        extracted_text = profile_data.get("extracted_text", "")
        if not extracted_text.strip():
            return None
        return build_profile(extracted_text)
    except Exception:
        return None


def load_resume_text():
    if not PROFILE_FILE.exists():
        return ""
    try:
        profile_data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        return profile_data.get("extracted_text", "")
    except Exception:
        return ""


# ============================================================
# BASIC ENDPOINTS
# ============================================================

@app.get("/")
def home():
    return {
        "success": True,
        "message": "Aryaman's Job Application Agent is running!",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Aryaman's Job Application Agent"
    }


# ============================================================
# RESUME UPLOAD (TEST 2)
# Supports .pdf, .docx, and .txt files
# ============================================================

def extract_pdf_text(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    text = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)
    return "\n".join(text)


def extract_docx_text(file_path: Path) -> str:
    document = Document(str(file_path))
    paragraphs = []
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            paragraphs.append(paragraph.text)
    return "\n".join(paragraphs)


@app.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    allowed_extensions = {".pdf", ".docx", ".txt"}
    original_filename = Path(file.filename or "resume").name
    file_extension = Path(original_filename).suffix.lower()

    if file_extension not in allowed_extensions:
        return {
            "success": False,
            "message": "Only PDF, DOCX, and TXT files are allowed."
        }

    destination = UPLOAD_DIR / original_filename

    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as error:
        return {
            "success": False,
            "message": "Failed to save uploaded resume.",
            "error": str(error)
        }

    try:
        if file_extension == ".pdf":
            extracted_text = extract_pdf_text(destination)
        elif file_extension == ".docx":
            extracted_text = extract_docx_text(destination)
        else:
            extracted_text = destination.read_text(encoding="utf-8")
    except Exception as error:
        return {
            "success": False,
            "message": "Resume was uploaded, but text extraction failed.",
            "error": str(error)
        }

    if not extracted_text.strip():
        return {
            "success": False,
            "message": "Resume text could not be extracted."
        }

    text_file = destination.with_suffix(".txt")
    text_file.write_text(extracted_text, encoding="utf-8")

    profile = {
        "filename": original_filename,
        "file_type": file_extension,
        "text_file": str(text_file),
        "text_length": len(extracted_text),
        "extracted_text": extracted_text
    }

    PROFILE_FILE.write_text(
        json.dumps(profile, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    return {
        "success": True,
        "filename": original_filename,
        "message": "Resume uploaded and text extracted successfully!",
        "text_length": len(extracted_text),
        "preview": extracted_text[:1000]
    }


# ============================================================
# RESUME PROFILE
# ============================================================

@app.get("/resume/profile")
def get_resume_profile():
    profile = load_current_profile()
    if profile is None:
        return {
            "success": False,
            "message": "No resume has been processed yet."
        }
    return {
        "success": True,
        "profile": profile
    }


# ============================================================
# AI RESUME ANALYSIS
# ============================================================

@app.get("/ai/resume-analysis")
def resume_analysis():
    profile = load_current_profile()
    if profile is None:
        return {
            "success": False,
            "message": "No resume has been processed yet."
        }
    try:
        analysis = analyze_resume(profile)
        return {
            "success": True,
            "analysis": analysis
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Resume analysis failed.",
            "error": str(error)
        }


# ============================================================
# AI JOB DESCRIPTION ANALYSIS
# ============================================================

@app.post("/ai/job-analysis")
def job_analysis(request: ATSRequest):
    if not request.job_description.strip():
        return {
            "success": False,
            "message": "Job description cannot be empty."
        }
    try:
        analysis = analyze_job_description(request.job_description)
        return {
            "success": True,
            "analysis": analysis
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Job description analysis failed.",
            "error": str(error)
        }


# ============================================================
# ATS SCORE
# ============================================================

@app.post("/ai/ats-score")
def ats_score(request: ATSRequest):
    resume_text = load_resume_text()
    if not resume_text:
        return {
            "success": False,
            "message": "No resume has been processed yet."
        }
    if not request.job_description.strip():
        return {
            "success": False,
            "message": "Job description cannot be empty."
        }
    try:
        result = calculate_ats_score(resume_text, request.job_description)
        return {
            "success": True,
            "ats": result
        }
    except Exception as error:
        return {
            "success": False,
            "message": "ATS scoring failed.",
            "error": str(error)
        }


# ============================================================
# OPTIMIZE RESUME
# ============================================================

@app.post("/ai/optimize-resume")
def optimize_resume_endpoint(request: ResumeOptimizeRequest):
    resume_text = load_resume_text()
    if not resume_text:
        return {
            "success": False,
            "message": "No resume has been processed yet."
        }
    if not request.job_description.strip():
        return {
            "success": False,
            "message": "Job description cannot be empty."
        }
    max_iterations = max(1, min(request.max_iterations, 8))
    try:
        result = optimize_until_90(
            resume_text,
            request.job_description,
            max_iterations=max_iterations
        )
        return {
            "success": True,
            "optimization": result
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Resume optimization failed.",
            "error": str(error)
        }


# ============================================================
# GENERATE TAILORED DOCX
# ============================================================

@app.post("/ai/generate-resume")
def generate_resume_endpoint(request: ResumeOptimizeRequest):
    resume_text = load_resume_text()
    if not resume_text:
        return {
            "success": False,
            "message": "No resume has been processed yet."
        }
    if not request.job_description.strip():
        return {
            "success": False,
            "message": "Job description cannot be empty."
        }
    max_iterations = max(1, min(request.max_iterations, 8))
    try:
        optimization = optimize_until_90(
            resume_text,
            request.job_description,
            max_iterations=max_iterations
        )
        optimized_resume = optimization.get("optimized_resume")
        if not optimized_resume:
            return {
                "success": False,
                "message": "AI optimization did not produce a resume.",
                "optimization": optimization
            }
        ats_result = optimization.get("final_ats")
        if not isinstance(ats_result, dict):
            ats_result = calculate_ats_score(optimized_resume, request.job_description)
        ats_score_val = ats_result.get("ats_score", 0)
        document = generate_tailored_resume(optimized_resume, ats_score_val, target_score=90)
        return {
            "success": document.get("success", False),
            "message": document.get("message", ""),
            "resume": document,
            "optimization": optimization,
            "ats": ats_result
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Tailored resume generation failed.",
            "error": str(error)
        }


# ============================================================
# AI JOB MATCHING
# ============================================================

@app.post("/ai/match-job")
def match_job_endpoint(request: ATSRequest):
    profile = load_current_profile()
    if profile is None:
        return {
            "success": False,
            "message": "No resume has been processed yet."
        }
    if not request.job_description.strip():
        return {
            "success": False,
            "message": "Job description cannot be empty."
        }
    try:
        result = match_job(profile, request.job_description)
        return {
            "success": True,
            "match": result
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Job matching failed.",
            "error": str(error)
        }


# ============================================================
# JOB PREFERENCES
# ============================================================

@app.post("/preferences")
def save_preferences(preferences: JobPreferences):
    preferences_data = preferences.model_dump()
    PREFERENCES_FILE.write_text(
        json.dumps(preferences_data, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )
    return {
        "success": True,
        "message": "Job preferences saved successfully.",
        "preferences": preferences_data
    }


@app.get("/preferences")
def get_preferences():
    if not PREFERENCES_FILE.exists():
        return {
            "success": False,
            "message": "No job preferences have been saved yet."
        }
    try:
        preferences = json.loads(PREFERENCES_FILE.read_text(encoding="utf-8"))
        return {
            "success": True,
            "preferences": preferences
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Failed to read job preferences.",
            "error": str(error)
        }


# ============================================================
# JOB SEARCH
# ============================================================

@app.get("/jobs/search")
def search_jobs(
    opportunity_type: str = "",
    work_mode: str = "",
    location: str = "",
    domains: str = ""
):
    if PREFERENCES_FILE.exists():
        try:
            saved_preferences = json.loads(PREFERENCES_FILE.read_text(encoding="utf-8"))
        except Exception:
            saved_preferences = {}
    else:
        saved_preferences = {}

    effective_opportunity_type = (
        opportunity_type.strip().lower()
        if opportunity_type.strip()
        else saved_preferences.get("opportunity_type", "internship").strip().lower()
    )
    effective_work_mode = (
        work_mode.strip().lower()
        if work_mode.strip()
        else saved_preferences.get("work_mode", "remote").strip().lower()
    )
    effective_location = (
        location.strip()
        if location.strip()
        else saved_preferences.get("location", "Anywhere")
    )

    if domains.strip():
        effective_domains = [domain.strip() for domain in domains.split(",") if domain.strip()]
    else:
        effective_domains = saved_preferences.get("domains", [])

    search_preferences = {
        "opportunity_type": effective_opportunity_type,
        "work_mode": effective_work_mode,
        "domains": effective_domains,
        "location": effective_location,
        "minimum_stipend": saved_preferences.get("minimum_stipend", 0),
        "experience_level": saved_preferences.get("experience_level", "Fresher")
    }

    try:
        jobs = get_all_jobs(search_term="", limit=100)
    except Exception as error:
        return {
            "success": False,
            "message": "Failed to retrieve jobs.",
            "error": str(error)
        }

    try:
        filtered_jobs = filter_jobs(jobs, search_preferences)
    except Exception as error:
        return {
            "success": False,
            "message": "Job filtering failed.",
            "error": str(error)
        }

    return {
        "success": True,
        "message": "Job search completed successfully.",
        "preferences_used": search_preferences,
        "jobs_retrieved": len(jobs),
        "jobs_found": len(filtered_jobs),
        "jobs": filtered_jobs
    }


# ============================================================
# APPLICATION STATS
# (Placed before /{application_id} to avoid route conflicts)
# ============================================================

@app.get("/applications/stats")
def applications_stats():
    try:
        stats = get_application_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Failed to retrieve application statistics.",
            "error": str(error)
        }


# ============================================================
# CREATE APPLICATION
# ============================================================

@app.post("/applications")
def create_application_endpoint(request: ApplicationCreateRequest):
    try:
        application = create_application(
            company=request.company,
            job_title=request.job_title,
            job_url=request.job_url,
            job_description=request.job_description,
            ats_score=request.ats_score,
            resume_version=request.resume_version,
            cover_letter=request.cover_letter,
            status=request.status,
            notes=request.notes
        )
        return {
            "success": True,
            "message": "Application created successfully.",
            "application": application
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Failed to create application.",
            "error": str(error)
        }


# ============================================================
# LIST APPLICATIONS
# ============================================================

@app.get("/applications")
def list_applications():
    try:
        applications = get_applications()
        return {
            "success": True,
            "count": len(applications),
            "applications": applications
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Failed to retrieve applications.",
            "error": str(error)
        }


# ============================================================
# GET SINGLE APPLICATION
# ============================================================

@app.get("/applications/{application_id}")
def get_application_endpoint(application_id: str):
    try:
        application = get_application(application_id)
        if application is None:
            return {
                "success": False,
                "message": "Application not found."
            }
        return {
            "success": True,
            "application": application
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Failed to retrieve application.",
            "error": str(error)
        }


# ============================================================
# UPDATE APPLICATION
# ============================================================

@app.patch("/applications/{application_id}")
def update_application_endpoint(application_id: str, request: ApplicationUpdateRequest):
    try:
        updates = request.model_dump(exclude_none=True)
        application = update_application(application_id, updates)
        if application is None:
            return {
                "success": False,
                "message": "Application not found."
            }
        return {
            "success": True,
            "message": "Application updated successfully.",
            "application": application
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Failed to update application.",
            "error": str(error)
        }


# ============================================================
# UPDATE APPLICATION STATUS
# ============================================================

@app.patch("/applications/{application_id}/status")
def update_application_status_endpoint(application_id: str, request: ApplicationStatusRequest):
    try:
        application = update_application_status(application_id, request.status)
        if application is None:
            return {
                "success": False,
                "message": "Application not found."
            }
        return {
            "success": True,
            "message": "Application status updated successfully.",
            "application": application
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Failed to update application status.",
            "error": str(error)
        }


# ============================================================
# DELETE APPLICATION
# ============================================================

@app.delete("/applications/{application_id}")
def delete_application_endpoint(application_id: str):
    try:
        deleted = delete_application(application_id)
        if not deleted:
            return {
                "success": False,
                "message": "Application not found."
            }
        return {
            "success": True,
            "message": "Application deleted successfully."
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Failed to delete application.",
            "error": str(error)
        }


# ============================================================
# COVER LETTER
# ============================================================

@app.post("/ai/cover-letter")
def cover_letter_endpoint(request: CoverLetterRequest):
    profile = load_current_profile()
    if profile is None:
        return {
            "success": False,
            "message": "No resume has been processed yet."
        }
    if not request.job_description.strip():
        return {
            "success": False,
            "message": "Job description cannot be empty."
        }
    try:
        result = generate_cover_letter(
            profile,
            request.job_description,
            company=request.company,
            job_title=request.job_title
        )
        return {
            "success": True,
            "cover_letter": result
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Cover letter generation failed.",
            "error": str(error)
        }


# ============================================================
# APPLICATION QUESTION ANALYSIS
# ============================================================

@app.post("/ai/application-question/analyze")
def application_question_analysis(request: ApplicationQuestionRequest):
    if not request.question.strip():
        return {
            "success": False,
            "message": "Question cannot be empty."
        }
    try:
        result = analyze_application_question(request.question, request.job_description)
        return {
            "success": True,
            "analysis": result
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Application question analysis failed.",
            "error": str(error)
        }


# ============================================================
# APPLICATION QUESTION ANSWER
# ============================================================

@app.post("/ai/application-question/answer")
def application_question_answer(request: ApplicationQuestionRequest):
    profile = load_current_profile()
    if profile is None:
        return {
            "success": False,
            "message": "No resume has been processed yet."
        }
    if not request.question.strip():
        return {
            "success": False,
            "message": "Question cannot be empty."
        }
    try:
        result = generate_application_answer(profile, request.question, request.job_description)
        return {
            "success": True,
            "answer": result
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Application answer generation failed.",
            "error": str(error)
        }


# ============================================================
# MULTIPLE APPLICATION QUESTIONS
# ============================================================

@app.post("/ai/application-questions/answers")
def application_questions_answers(request: ApplicationQuestionsRequest):
    profile = load_current_profile()
    if profile is None:
        return {
            "success": False,
            "message": "No resume has been processed yet."
        }
    if not request.questions:
        return {
            "success": False,
            "message": "At least one question is required."
        }
    try:
        result = generate_application_answers(profile, request.questions, request.job_description)
        return {
            "success": True,
            "answers": result
        }
    except Exception as error:
        return {
            "success": False,
            "message": "Application answers generation failed.",
            "error": str(error)
        }


# ============================================================
# AI CONNECTION TEST (TEST 24)
# ============================================================

@app.get("/ai/test")
def test_ai():
    try:
        response = ask_gemini(
            "You are the AI assistant inside Aryaman's Job Application Agent. "
            "Reply in one short sentence confirming that you are connected."
        )
        return {
            "success": True,
            "message": response
        }
    except Exception as error:
        return {
            "success": False,
            "message": "AI connection test failed.",
            "error": str(error)
        }


# ============================================================
# END-TO-END WORKFLOW TEST (TEST 25)
# ============================================================

@app.post("/workflow/e2e-test")
def workflow_e2e_test(request: WorkflowE2ERequest):
    """
    Complete end-to-end flow:
    1. Read uploaded profile
    2. Analyze job description
    3. Calculate initial ATS score
    4. Optimize resume to 90+ using Gemini
    5. Generate tailored .docx document
    6. Generate tailored cover letter
    7. Save tracked job application
    """
    resume_text = load_resume_text()
    profile = load_current_profile()

    if not resume_text or profile is None:
        return {
            "success": False,
            "message": "No resume has been processed yet. Run Test 2 (/resume/upload) first."
        }

    if not request.job_description.strip():
        return {
            "success": False,
            "message": "Job description cannot be empty."
        }

    try:
        # 1. Job Analysis
        job_analysis_data = analyze_job_description(request.job_description)

        # 2. Initial ATS score
        initial_ats = calculate_ats_score(resume_text, request.job_description, job_analysis_data)

        # 3. Optimize until 90+
        optimization = optimize_until_90(resume_text, request.job_description, max_iterations=4)
        optimized_resume_text = optimization.get("optimized_resume", resume_text)
        final_score = optimization.get("final_score", {}).get("ats_score", initial_ats.get("ats_score", 0))

        # 4. Generate Tailored Word Document
        document_result = generate_tailored_resume(optimized_resume_text, final_score, target_score=90)

        # 5. Generate Tailored Cover Letter
        cover_letter_text = generate_cover_letter(
            profile,
            request.job_description,
            company=request.company,
            job_title=request.job_title
        )

        # 6. Save in Applications Tracker
        created_app = None
        if request.save_application:
            created_app = create_application(
                company=request.company,
                job_title=request.job_title,
                job_description=request.job_description,
                ats_score=float(final_score),
                resume_version=document_result.get("filename", "tailored_resume.docx"),
                cover_letter=cover_letter_text,
                status="Ready to Apply",
                notes="Automated E2E pipeline completed."
            )

        return {
            "success": True,
            "message": "End-to-End workflow completed successfully!",
            "workflow": {
                "initial_ats_score": initial_ats.get("ats_score", 0),
                "final_ats_score": final_score,
                "target_reached": optimization.get("target_reached", False),
                "generated_docx": document_result.get("filename", ""),
                "cover_letter_generated": bool(cover_letter_text),
                "application_id": created_app.get("id") if created_app else None
            }
        }
    except Exception as error:
        return {
            "success": False,
            "message": "End-to-end workflow failed.",
            "error": str(error)
        }