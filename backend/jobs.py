from __future__ import annotations

import re
from typing import Any

import requests


# ============================================================
# JOB SOURCES
# ============================================================

REMOTIVE_URL = (
    "https://remotive.com/api/remote-jobs"
)

ARBEITNOW_URL = (
    "https://www.arbeitnow.com/api/job-board-api"
)

REQUEST_TIMEOUT = 20


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(value: Any) -> str:
    """
    Convert any value to normalized searchable text.
    """

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def normalize_lower(value: Any) -> str:
    """
    Normalize text and convert it to lowercase.
    """

    return normalize_text(value).lower()


def contains_term(
    text: str,
    term: str
) -> bool:
    """
    Check whether a term appears as a meaningful word/phrase.
    """

    text = normalize_lower(text)
    term = normalize_lower(term)

    if not text or not term:
        return False

    pattern = (
        r"(?<!\w)"
        + re.escape(term)
        + r"(?!\w)"
    )

    return bool(
        re.search(
            pattern,
            text
        )
    )


# ============================================================
# REMOTIVE
# ============================================================

def get_remote_jobs(
    search_term: str = "",
    limit: int = 50
) -> list[dict]:
    """
    Retrieve remote jobs from Remotive.
    """

    params = {}

    if search_term.strip():

        params["search"] = (
            search_term.strip()
        )

    response = requests.get(
        REMOTIVE_URL,
        params=params,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    jobs = data.get(
        "jobs",
        []
    )

    return jobs[:limit]


# ============================================================
# ARBEITNOW
# ============================================================

def get_arbeitnow_jobs(
    search_term: str = "",
    limit: int = 50
) -> list[dict]:
    """
    Retrieve jobs from Arbeitnow.
    """

    response = requests.get(
        ARBEITNOW_URL,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    jobs = data.get(
        "data",
        []
    )

    if search_term.strip():

        search = normalize_lower(
            search_term
        )

        filtered = []

        for job in jobs:

            searchable = " ".join(
                [
                    normalize_text(
                        job.get(
                            "title",
                            ""
                        )
                    ),

                    normalize_text(
                        job.get(
                            "description",
                            ""
                        )
                    ),

                    normalize_text(
                        job.get(
                            "company_name",
                            ""
                        )
                    ),

                    normalize_text(
                        job.get(
                            "location",
                            ""
                        )
                    )
                ]
            ).lower()

            if search in searchable:

                filtered.append(
                    job
                )

        jobs = filtered

    return jobs[:limit]


# ============================================================
# NORMALIZE JOB
# ============================================================

def normalize_job(
    job: dict,
    source: str
) -> dict:
    """
    Convert different job-board formats into one common format.
    """

    if source == "remotive":

        title = normalize_text(
            job.get(
                "title",
                ""
            )
        )

        company = normalize_text(
            job.get(
                "company_name",
                ""
            )
        )

        url = normalize_text(
            job.get(
                "url",
                ""
            )
        )

        category = normalize_text(
            job.get(
                "category",
                ""
            )
        )

        job_type = normalize_text(
            job.get(
                "job_type",
                ""
            )
        )

        location = normalize_text(
            job.get(
                "candidate_required_location",
                ""
            )
        )

        salary = normalize_text(
            job.get(
                "salary",
                ""
            )
        )

        description = normalize_text(
            job.get(
                "description",
                ""
            )
        )

        publication_date = normalize_text(
            job.get(
                "publication_date",
                ""
            )
        )

        return {

            "id":
                str(
                    job.get(
                        "id",
                        ""
                    )
                ),

            "source":
                "Remotive",

            "title":
                title,

            "company":
                company,

            "url":
                url,

            "category":
                category,

            "job_type":
                job_type,

            "location":
                location,

            "salary":
                salary,

            "publication_date":
                publication_date,

            "description":
                description
        }

    # --------------------------------------------------------
    # ARBEITNOW
    # --------------------------------------------------------

    title = normalize_text(
        job.get(
            "title",
            ""
        )
    )

    company = normalize_text(
        job.get(
            "company_name",
            job.get(
                "company",
                ""
            )
        )
    )

    url = normalize_text(
        job.get(
            "url",
            ""
        )
    )

    category = normalize_text(
        job.get(
            "job_types",
            job.get(
                "category",
                ""
            )
        )
    )

    job_type = normalize_text(
        job.get(
            "job_types",
            ""
        )
    )

    location = normalize_text(
        job.get(
            "location",
            ""
        )
    )

    salary = normalize_text(
        job.get(
            "salary",
            ""
        )
    )

    description = normalize_text(
        job.get(
            "description",
            ""
        )
    )

    publication_date = normalize_text(
        job.get(
            "created_at",
            ""
        )
    )

    return {

        "id":
            str(
                job.get(
                    "slug",
                    job.get(
                        "id",
                        ""
                    )
                )
            ),

        "source":
            "Arbeitnow",

        "title":
            title,

        "company":
            company,

        "url":
            url,

        "category":
            category,

        "job_type":
            job_type,

        "location":
            location,

        "salary":
            salary,

        "publication_date":
            publication_date,

        "description":
            description
    }


# ============================================================
# GET ALL JOBS
# ============================================================

def get_all_jobs(
    search_term: str = "",
    limit: int = 100
) -> list[dict]:
    """
    Retrieve jobs from all configured sources.

    Duplicate jobs are removed using URL/title/company.
    """

    all_jobs = []

    # --------------------------------------------------------
    # REMOTIVE
    # --------------------------------------------------------

    try:

        remotive_jobs = get_remote_jobs(
            search_term=search_term,
            limit=limit
        )

        for job in remotive_jobs:

            all_jobs.append(
                normalize_job(
                    job,
                    "remotive"
                )
            )

    except Exception:

        pass

    # --------------------------------------------------------
    # ARBEITNOW
    # --------------------------------------------------------

    try:

        arbeitnow_jobs = get_arbeitnow_jobs(
            search_term=search_term,
            limit=limit
        )

        for job in arbeitnow_jobs:

            all_jobs.append(
                normalize_job(
                    job,
                    "arbeitnow"
                )
            )

    except Exception:

        pass

    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    unique_jobs = []

    seen = set()

    for job in all_jobs:

        identity = (

            normalize_lower(
                job.get(
                    "url",
                    ""
                )
            )

            or

            (
                normalize_lower(
                    job.get(
                        "title",
                        ""
                    )
                ),

                normalize_lower(
                    job.get(
                        "company",
                        ""
                    )
                )
            )
        )

        if identity in seen:

            continue

        seen.add(
            identity
        )

        unique_jobs.append(
            job
        )

    return unique_jobs[:limit]


# ============================================================
# OPPORTUNITY TYPE
# ============================================================

def normalize_job_type(
    value: str
) -> str:
    """
    Normalize job-type terminology.
    """

    value = normalize_lower(
        value
    )

    if any(
        term in value
        for term in [
            "intern",
            "internship",
            "trainee"
        ]
    ):

        return "internship"

    if any(
        term in value
        for term in [
            "part time",
            "part-time"
        ]
    ):

        return "part-time"

    if any(
        term in value
        for term in [
            "full time",
            "full-time",
            "permanent"
        ]
    ):

        return "full-time"

    return value


def matches_opportunity_type(
    job: dict,
    opportunity_type: str
) -> bool:
    """
    Determine whether a job matches the requested opportunity type.
    """

    requested = normalize_job_type(
        opportunity_type
    )

    if not requested:

        return True

    job_type = normalize_job_type(
        job.get(
            "job_type",
            ""
        )
    )

    title = normalize_lower(
        job.get(
            "title",
            ""
        )
    )

    description = normalize_lower(
        job.get(
            "description",
            ""
        )
    )

    searchable = " ".join(
        [
            job_type,
            title,
            description
        ]
    )

    if requested == "internship":

        return any(
            term in searchable
            for term in [
                "intern",
                "internship",
                "trainee"
            ]
        )

    if requested == "part-time":

        return (
            "part-time" in searchable
            or
            "part time" in searchable
        )

    if requested == "full-time":

        # Full-time listings frequently don't explicitly
        # contain "full-time". Reject clearly incompatible
        # listings but allow unspecified job types.

        if (
            "internship" in searchable
            or "intern" in searchable
            or "part-time" in searchable
            or "part time" in searchable
        ):

            return False

        return True

    return (
        requested in searchable
    )


# ============================================================
# WORK MODE
# ============================================================

def matches_work_mode(
    job: dict,
    work_mode: str
) -> bool:
    """
    Match remote / hybrid / onsite preferences.
    """

    requested = normalize_lower(
        work_mode
    )

    if not requested:

        return True

    if requested in {
        "any",
        "anywhere",
        "all"
    }:

        return True

    location = normalize_lower(
        job.get(
            "location",
            ""
        )
    )

    description = normalize_lower(
        job.get(
            "description",
            ""
        )
    )

    combined = (
        location
        + " "
        + description
    )

    if requested == "remote":

        return any(
            term in combined
            for term in [
                "remote",
                "work from home",
                "worldwide",
                "anywhere"
            ]
        )

    if requested == "hybrid":

        return "hybrid" in combined

    if requested in {
        "onsite",
        "on-site",
        "office"
    }:

        if "remote" in combined:

            return False

        if "hybrid" in combined:

            return False

        return True

    return True


# ============================================================
# LOCATION
# ============================================================

def matches_location(
    job: dict,
    requested_location: str
) -> bool:
    """
    Match requested location.

    Generic locations such as Anywhere, Worldwide and India
    do not unnecessarily exclude remote jobs.
    """

    requested = normalize_lower(
        requested_location
    )

    if requested in {
        "",
        "any",
        "anywhere",
        "worldwide",
        "global"
    }:

        return True

    location = normalize_lower(
        job.get(
            "location",
            ""
        )
    )

    description = normalize_lower(
        job.get(
            "description",
            ""
        )
    )

    combined = (
        location
        + " "
        + description
    )

    # Remote jobs can generally be performed from the requested
    # country/region unless the listing explicitly restricts it.

    remote_terms = [
        "remote",
        "work from home",
        "worldwide",
        "anywhere"
    ]

    if any(
        term in location
        for term in remote_terms
    ):

        return True

    return (
        requested in combined
    )


# ============================================================
# SALARY
# ============================================================

def extract_salary_numbers(
    salary: str
) -> list[float]:
    """
    Extract numeric salary values from salary text.
    """

    salary = normalize_text(
        salary
    )

    if not salary:

        return []

    matches = re.findall(
        r"\d+(?:,\d+)*(?:\.\d+)?",
        salary
    )

    numbers = []

    for match in matches:

        try:

            numbers.append(
                float(
                    match.replace(
                        ",",
                        ""
                    )
                )
            )

        except ValueError:

            continue

    return numbers


def matches_minimum_salary(
    job: dict,
    minimum_salary: int | float
) -> tuple[bool, bool]:
    """
    Returns:
        (matches, salary_verified)

    Unknown salary is allowed through so that potentially useful
    jobs aren't discarded.
    """

    try:

        minimum_salary = float(
            minimum_salary
        )

    except (
        TypeError,
        ValueError
    ):

        minimum_salary = 0

    if minimum_salary <= 0:

        return True, False

    salary = normalize_text(
        job.get(
            "salary",
            ""
        )
    )

    numbers = extract_salary_numbers(
        salary
    )

    if not numbers:

        return True, False

    maximum_salary = max(
        numbers
    )

    return (
        maximum_salary >= minimum_salary,
        True
    )


# ============================================================
# EXPERIENCE LEVEL
# ============================================================

def matches_experience_level(
    job: dict,
    experience_level: str
) -> bool:
    """
    Match broad experience preferences.
    """

    requested = normalize_lower(
        experience_level
    )

    if requested in {
        "",
        "any",
        "all"
    }:

        return True

    title = normalize_lower(
        job.get(
            "title",
            ""
        )
    )

    description = normalize_lower(
        job.get(
            "description",
            ""
        )
    )

    combined = (
        title
        + " "
        + description
    )

    if requested in {
        "fresher",
        "entry",
        "entry-level",
        "entry level"
    }:

        if any(
            term in combined
            for term in [
                "senior",
                "lead",
                "principal",
                "manager",
                "director",
                "head of"
            ]
        ):

            return False

        return True

    if requested in {
        "mid",
        "mid-level",
        "mid level"
    }:

        return not any(
            term in combined
            for term in [
                "senior",
                "principal",
                "director"
            ]
        )

    if requested in {
        "senior",
        "experienced"
    }:

        return any(
            term in combined
            for term in [
                "senior",
                "lead",
                "principal",
                "manager"
            ]
        )

    return True


# ============================================================
# DOMAIN MATCHING
# ============================================================

def get_domain_matches(
    job: dict,
    domains: list[str]
) -> list[str]:
    """
    Determine whether user-specified domains are represented
    in the job.

    This function does NOT contain a fixed domain dictionary.

    The user's domain itself is searched in the job text.
    """

    if not domains:

        return []

    title = normalize_lower(
        job.get(
            "title",
            ""
        )
    )

    category = normalize_lower(
        job.get(
            "category",
            ""
        )
    )

    description = normalize_lower(
        job.get(
            "description",
            ""
        )
    )

    combined = " ".join(
        [
            title,
            category,
            description
        ]
    )

    matches = []

    for domain in domains:

        domain = normalize_text(
            domain
        )

        if not domain:

            continue

        domain_lower = domain.lower()

        # Search the exact user-specified domain.
        if contains_term(
            combined,
            domain_lower
        ):

            matches.append(
                domain
            )

            continue

        # Also support slash/hyphen/space variations.
        variations = {
            domain_lower.replace(
                "/",
                " "
            ),

            domain_lower.replace(
                "-",
                " "
            ),

            domain_lower.replace(
                " ",
                "/"
            ),

            domain_lower.replace(
                " ",
                "-"
            )
        }

        if any(
            contains_term(
                combined,
                variation
            )
            for variation in variations
            if variation
        ):

            matches.append(
                domain
            )

    return matches


# ============================================================
# JOB SCORING
# ============================================================

def calculate_job_score(
    job: dict,
    preferences: dict
) -> tuple[int, list[str], bool]:
    """
    Calculate a lightweight relevance score.

    AI matching remains the more advanced matching layer.
    """

    score = 0

    reasons = []

    domains = preferences.get(
        "domains",
        []
    )

    matched_domains = get_domain_matches(
        job,
        domains
    )

    if matched_domains:

        score += 35

        reasons.append(
            "Matches selected domain"
        )

    opportunity_type = preferences.get(
        "opportunity_type",
        ""
    )

    if matches_opportunity_type(
        job,
        opportunity_type
    ):

        score += 20

        if opportunity_type:

            reasons.append(
                "Matches opportunity type"
            )

    work_mode = preferences.get(
        "work_mode",
        ""
    )

    if matches_work_mode(
        job,
        work_mode
    ):

        score += 15

        if work_mode:

            reasons.append(
                "Matches work mode"
            )

    location = preferences.get(
        "location",
        ""
    )

    if matches_location(
        job,
        location
    ):

        score += 10

        if location:

            reasons.append(
                "Matches location"
            )

    experience_level = preferences.get(
        "experience_level",
        ""
    )

    if matches_experience_level(
        job,
        experience_level
    ):

        score += 10

    minimum_salary = preferences.get(
        "minimum_stipend",
        0
    )

    salary_matches, salary_verified = (
        matches_minimum_salary(
            job,
            minimum_salary
        )
    )

    if salary_matches:

        score += 10

        if salary_verified:

            reasons.append(
                "Meets minimum salary/stipend"
            )

        else:

            reasons.append(
                "Salary not specified"
            )

    return (
        min(score, 100),
        reasons,
        salary_verified
    )


# ============================================================
# FILTER JOBS
# ============================================================

def filter_jobs(
    jobs: list[dict],
    preferences: dict
) -> list[dict]:
    """
    Filter and rank jobs using user preferences.
    """

    filtered = []

    for job in jobs:

        if not matches_opportunity_type(
            job,
            preferences.get(
                "opportunity_type",
                ""
            )
        ):

            continue

        if not matches_work_mode(
            job,
            preferences.get(
                "work_mode",
                ""
            )
        ):

            continue

        if not matches_location(
            job,
            preferences.get(
                "location",
                ""
            )
        ):

            continue

        if not matches_experience_level(
            job,
            preferences.get(
                "experience_level",
                ""
            )
        ):

            continue

        salary_matches, salary_verified = (
            matches_minimum_salary(
                job,
                preferences.get(
                    "minimum_stipend",
                    0
                )
            )
        )

        if not salary_matches:

            continue

        domains = preferences.get(
            "domains",
            []
        )

        # If domains were explicitly supplied, require at least
        # one domain match.
        if domains:

            matched_domains = get_domain_matches(
                job,
                domains
            )

            if not matched_domains:

                continue

        else:

            matched_domains = []

        score, reasons, verified = (
            calculate_job_score(
                job,
                preferences
            )
        )

        job_copy = dict(
            job
        )

        job_copy[
            "matched_domains"
        ] = matched_domains

        job_copy[
            "match_score"
        ] = score

        job_copy[
            "match_reasons"
        ] = reasons

        job_copy[
            "salary_verified"
        ] = verified

        filtered.append(
            job_copy
        )

    filtered.sort(
        key=lambda item: item.get(
            "match_score",
            0
        ),
        reverse=True
    )

    return filtered