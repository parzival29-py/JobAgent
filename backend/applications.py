from datetime import datetime, timezone
from pathlib import Path
import json
import uuid


# ============================================================
# APPLICATION STORAGE
# ============================================================

UPLOAD_DIR = Path("uploads")
APPLICATIONS_FILE = UPLOAD_DIR / "applications.json"

UPLOAD_DIR.mkdir(exist_ok=True)


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _load_applications() -> list[dict]:
    """
    Load all saved applications.
    """

    if not APPLICATIONS_FILE.exists():
        return []

    try:
        data = json.loads(
            APPLICATIONS_FILE.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(data, list):
            return data

        return []

    except Exception:
        return []


def _save_applications(applications: list[dict]) -> None:
    """
    Save all applications to disk.
    """

    APPLICATIONS_FILE.write_text(
        json.dumps(
            applications,
            indent=4,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )


def _utc_now() -> str:
    """
    Return the current UTC time as an ISO timestamp.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# CREATE APPLICATION
# ============================================================

def create_application(
    company: str,
    job_title: str,
    job_url: str = "",
    job_description: str = "",
    ats_score: float | None = None,
    resume_version: str = "",
    cover_letter: str = "",
    status: str = "Saved",
    notes: str = ""
) -> dict:
    """
    Create and save a new job application.
    """

    applications = _load_applications()

    application = {

        "id": str(
            uuid.uuid4()
        ),

        "company": company.strip(),

        "job_title": job_title.strip(),

        "job_url": job_url.strip(),

        "job_description":
            job_description.strip(),

        "ats_score":
            ats_score,

        "resume_version":
            resume_version.strip(),

        "cover_letter":
            cover_letter,

        "status":
            status.strip() or "Saved",

        "notes":
            notes.strip(),

        "created_at":
            _utc_now(),

        "updated_at":
            _utc_now(),

        "applied_at":
            None
    }

    applications.append(
        application
    )

    _save_applications(
        applications
    )

    return application


# ============================================================
# GET ALL APPLICATIONS
# ============================================================

def get_applications() -> list[dict]:
    """
    Return all saved applications.
    """

    applications = _load_applications()

    # Newest applications first
    applications.sort(
        key=lambda item:
            item.get(
                "created_at",
                ""
            ),
        reverse=True
    )

    return applications


# ============================================================
# GET SINGLE APPLICATION
# ============================================================

def get_application(
    application_id: str
) -> dict | None:
    """
    Find one application by ID.
    """

    applications = _load_applications()

    for application in applications:

        if application.get("id") == application_id:

            return application

    return None


# ============================================================
# UPDATE APPLICATION STATUS
# ============================================================

def update_application_status(
    application_id: str,
    status: str
) -> dict | None:
    """
    Update the status of an application.
    """

    applications = _load_applications()

    for application in applications:

        if application.get("id") == application_id:

            application["status"] = (
                status.strip()
                or "Saved"
            )

            application["updated_at"] = (
                _utc_now()
            )

            # Record when the application
            # was actually submitted.
            if (
                application["status"].lower()
                == "applied"
                and not application.get(
                    "applied_at"
                )
            ):

                application["applied_at"] = (
                    _utc_now()
                )

            _save_applications(
                applications
            )

            return application

    return None


# ============================================================
# UPDATE APPLICATION
# ============================================================

def update_application(
    application_id: str,
    updates: dict
) -> dict | None:
    """
    Update supported fields of an application.
    """

    allowed_fields = {

        "company",

        "job_title",

        "job_url",

        "job_description",

        "ats_score",

        "resume_version",

        "cover_letter",

        "status",

        "notes"
    }

    applications = _load_applications()

    for application in applications:

        if application.get("id") != application_id:
            continue

        for field, value in updates.items():

            if field not in allowed_fields:
                continue

            if field in {
                "company",
                "job_title",
                "job_url",
                "job_description",
                "resume_version",
                "cover_letter",
                "notes",
                "status"
            }:

                if value is None:
                    continue

                application[field] = str(
                    value
                ).strip()

            elif field == "ats_score":

                application[field] = value

        application["updated_at"] = (
            _utc_now()
        )

        if (
            application.get("status", "")
            .lower()
            == "applied"
            and not application.get(
                "applied_at"
            )
        ):

            application["applied_at"] = (
                _utc_now()
            )

        _save_applications(
            applications
        )

        return application

    return None


# ============================================================
# DELETE APPLICATION
# ============================================================

def delete_application(
    application_id: str
) -> bool:
    """
    Delete an application by ID.
    """

    applications = _load_applications()

    original_count = len(
        applications
    )

    applications = [

        application

        for application in applications

        if application.get("id")
        != application_id
    ]

    if len(applications) == original_count:

        return False

    _save_applications(
        applications
    )

    return True


# ============================================================
# APPLICATION STATISTICS
# ============================================================

def get_application_stats() -> dict:
    """
    Return useful application statistics.
    """

    applications = _load_applications()

    total = len(
        applications
    )

    status_counts = {}

    for application in applications:

        status = (
            application.get(
                "status",
                "Saved"
            )
            or "Saved"
        )

        status = status.strip()

        status_counts[status] = (
            status_counts.get(
                status,
                0
            )
            + 1
        )

    applied = sum(

        1

        for application in applications

        if application.get(
            "status",
            ""
        ).lower()
        == "applied"
    )

    interviews = sum(

        1

        for application in applications

        if application.get(
            "status",
            ""
        ).lower()
        == "interview"
    )

    offers = sum(

        1

        for application in applications

        if application.get(
            "status",
            ""
        ).lower()
        == "offer"
    )

    rejected = sum(

        1

        for application in applications

        if application.get(
            "status",
            ""
        ).lower()
        == "rejected"
    )

    return {

        "total_applications":
            total,

        "applied":
            applied,

        "interviews":
            interviews,

        "offers":
            offers,

        "rejected":
            rejected,

        "status_counts":
            status_counts
    }