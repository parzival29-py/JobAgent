import requests


# ============================================================
# REMOTIVE
# ============================================================

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"


def get_remotive_jobs(search_term: str = "", limit: int = 50):
    """
    Get jobs from Remotive and convert them into our
    common job format.
    """

    params = {
        "limit": limit
    }

    if search_term:
        params["search"] = search_term

    response = requests.get(
        REMOTIVE_API_URL,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    jobs = []

    for job in data.get("jobs", []):

        jobs.append({
            "id": f"remotive-{job.get('id')}",
            "source": "Remotive",
            "title": job.get("title"),
            "company": job.get("company_name"),
            "url": job.get("url"),
            "category": job.get("category"),
            "job_type": job.get("job_type"),
            "location": job.get("candidate_required_location"),
            "salary": job.get("salary"),
            "publication_date": job.get("publication_date"),
            "description": job.get("description"),
        })

    return jobs


# ============================================================
# ARBEITNOW
# ============================================================

ARBEITNOW_API_URL = (
    "https://www.arbeitnow.com/api/job-board-api"
)


def get_arbeitnow_jobs(
    search_term: str = "",
    limit: int = 50
):
    """
    Get jobs from Arbeitnow and convert them into the
    same common format used by Remotive.
    """

    response = requests.get(
        ARBEITNOW_API_URL,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    jobs = []

    for job in data.get("data", []):

        title = job.get("title") or ""
        description = job.get("description") or ""
        location = job.get("location") or ""

        # Optional keyword filtering at source level.
        if search_term:

            search_text = (
                title + " " +
                description + " " +
                location
            ).lower()

            if search_term.lower() not in search_text:
                continue

        # Determine job type from Arbeitnow tags.
        tags = job.get("tags") or []

        job_type = ""

        for tag in tags:

            tag_text = str(tag).lower()

            if "full" in tag_text:
                job_type = "full_time"
                break

            if "part" in tag_text:
                job_type = "part_time"
                break

            if "intern" in tag_text:
                job_type = "internship"
                break

        jobs.append({

            "id": f"arbeitnow-{job.get('slug') or job.get('id')}",

            "source": "Arbeitnow",

            "title": title,

            "company": job.get("company_name"),

            "url": job.get("url"),

            "category": ", ".join(
                str(tag)
                for tag in tags
            ),

            "job_type": job_type,

            "location": location,

            "salary": "",

            "publication_date": job.get("created_at"),

            "description": description,

            # Arbeitnow exposes whether a job is remote.
            "remote": job.get("remote", False),
        })

        if len(jobs) >= limit:
            break

    return jobs


# ============================================================
# GET JOBS FROM ALL SOURCES
# ============================================================

def get_all_jobs(
    search_term: str = "",
    limit_per_source: int = 50
):
    """
    Retrieve jobs from every connected job source.
    """

    all_jobs = []

    # --------------------------------------------------------
    # REMOTIVE
    # --------------------------------------------------------

    try:

        remotive_jobs = get_remotive_jobs(
            search_term=search_term,
            limit=limit_per_source
        )

        all_jobs.extend(remotive_jobs)

    except Exception as error:

        print(
            "Remotive error:",
            error
        )

    # --------------------------------------------------------
    # ARBEITNOW
    # --------------------------------------------------------

    try:

        arbeitnow_jobs = get_arbeitnow_jobs(
            search_term=search_term,
            limit=limit_per_source
        )

        all_jobs.extend(arbeitnow_jobs)

    except Exception as error:

        print(
            "Arbeitnow error:",
            error
        )

    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    unique_jobs = {}

    for job in all_jobs:

        job_id = job.get("id")

        if not job_id:
            continue

        unique_jobs[job_id] = job

    return list(
        unique_jobs.values()
    )