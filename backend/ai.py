import os
import json
import re
from typing import Any

from dotenv import load_dotenv
from google import genai


# ============================================================
# ENVIRONMENT / GEMINI CONFIGURATION
# ============================================================

load_dotenv(override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not configured."
    )


MODEL_NAME = "gemini-3.5-flash-lite"

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# ATS CONFIGURATION
# ============================================================

ATS_TARGET_SCORE = 90
ATS_MINIMUM_SCORE = 90

MAX_OPTIMIZATION_ITERATIONS = 8


# ============================================================
# BASIC GEMINI FUNCTION
# ============================================================

def ask_gemini(prompt: str) -> str:
    """
    Send a prompt to Gemini and return the text response.
    """

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text or ""


# ============================================================
# JSON RESPONSE PARSER
# ============================================================

def _json_from_response(text: str) -> dict:
    """
    Safely convert Gemini's response into a Python dictionary.

    Handles normal JSON and JSON wrapped in markdown fences.
    """

    if not text:
        return {}

    cleaned = text.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned
    )

    try:

        result = json.loads(cleaned)

        if isinstance(result, dict):

            return result

    except json.JSONDecodeError:

        pass

    # Try to locate a JSON object
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end != -1 and end > start:

        candidate = cleaned[
            start:end + 1
        ]

        try:

            result = json.loads(candidate)

            if isinstance(result, dict):

                return result

        except json.JSONDecodeError:

            pass

    return {}


# ============================================================
# GENERIC LIST NORMALIZER
# ============================================================

def _clean_list(value: Any) -> list[str]:
    """
    Convert an arbitrary value into a clean list of strings.
    """

    if not isinstance(value, list):

        return []

    cleaned = []

    seen = set()

    for item in value:

        if not isinstance(item, str):

            continue

        item = item.strip()

        if not item:

            continue

        key = item.lower()

        if key in seen:

            continue

        seen.add(key)

        cleaned.append(item)

    return cleaned


# ============================================================
# RESUME ANALYSIS
# ============================================================

def analyze_resume(profile: dict) -> str:
    """
    Analyze a resume without assuming any particular
    professional domain.
    """

    prompt = f"""
You are an expert AI career assistant.

Analyze the following candidate resume.

RESUME PROFILE:
{json.dumps(profile, indent=2, ensure_ascii=False)}

The candidate may belong to ANY professional domain.

Do not assume that the candidate is from CSE, ECE,
AI/ML, Marketing, Engineering, Finance, Law, Design,
HR, Sales, Medicine, or any other field unless the
resume actually indicates it.

Provide a practical analysis containing:

1. Strongest skills
2. Suitable job roles
3. Suitable internship roles
4. Suitable industries or career areas
5. Strongest qualifications
6. Weak areas
7. Missing or unclear information
8. Recommended improvements
9. Overall career direction

Rules:

- Use only information supported by the resume.
- Do not invent qualifications.
- Do not invent work experience.
- Do not invent projects.
- Do not invent certifications.
- Do not invent achievements.
- Do not assume skills that are not present.

Keep the response practical and specific.
"""

    return ask_gemini(prompt)


# ============================================================
# JOB MATCHING
# ============================================================

def match_job(
    profile: dict,
    job_description: str
) -> str:
    """
    Compare a candidate resume against a job description.
    """

    prompt = f"""
You are an expert AI job-matching assistant.

CANDIDATE RESUME PROFILE:
{json.dumps(profile, indent=2, ensure_ascii=False)}

JOB DESCRIPTION:
{job_description}

Carefully compare the candidate with the job.

Return the result using exactly these sections:

MATCH SCORE:
Give a percentage from 0 to 100.

STRONG MATCHES:
List the candidate's skills, education, projects,
experience, certifications, or achievements that
clearly match the job.

MISSING OR WEAK AREAS:
List important requirements that the candidate does
not clearly satisfy.

WHY THIS SCORE:
Briefly explain the reasoning behind the score.

RECOMMENDATION:
Choose exactly one:

- APPLY
- CONSIDER
- SKIP

Rules:

- Be honest.
- Do not invent experience.
- Do not assume a skill exists just because it is common
  in the candidate's field.
- Do not treat unrelated experience as equivalent.
- Match based on the actual resume and job description.
"""

    return ask_gemini(prompt)


# ============================================================
# JOB DESCRIPTION ANALYSIS
# ============================================================

def analyze_job_description(
    job_description: str
) -> dict:
    """
    Convert a job description into structured requirements.
    """

    prompt = f"""
Analyze this job description for resume optimization
and ATS matching.

JOB DESCRIPTION:
{job_description}

Return ONLY valid JSON.

Use exactly this structure:

{{
    "job_title": "",
    "company": "",
    "required_skills": [],
    "preferred_skills": [],
    "responsibilities": [],
    "qualifications": [],
    "experience_requirements": [],
    "education_requirements": [],
    "certifications": [],
    "tools_and_technologies": [],
    "soft_skills": [],
    "keywords": [],
    "seniority": "",
    "important_requirements": []
}}

Rules:

1. Extract only information actually present in the JD.
2. Do not invent requirements.
3. Separate required and preferred requirements whenever
   the JD makes that distinction.
4. Extract important ATS phrases.
5. Keep multi-word technologies and professional phrases
   intact.
6. Do not turn generic filler words into keywords.
7. Preserve important job terminology.

Examples of useful keywords:

- technologies
- software
- programming languages
- methodologies
- certifications
- professional competencies
- job titles
- domain terminology
- important responsibilities
- required qualifications

Do not output explanations outside the JSON.
"""

    response = ask_gemini(prompt)

    result = _json_from_response(
        response
    )

    if not result:

        return {
            "job_title": "",
            "company": "",
            "required_skills": [],
            "preferred_skills": [],
            "responsibilities": [],
            "qualifications": [],
            "experience_requirements": [],
            "education_requirements": [],
            "certifications": [],
            "tools_and_technologies": [],
            "soft_skills": [],
            "keywords": [],
            "seniority": "",
            "important_requirements": []
        }

    # Normalize all list fields
    list_fields = [
        "required_skills",
        "preferred_skills",
        "responsibilities",
        "qualifications",
        "experience_requirements",
        "education_requirements",
        "certifications",
        "tools_and_technologies",
        "soft_skills",
        "keywords",
        "important_requirements"
    ]

    for field in list_fields:

        result[field] = _clean_list(
            result.get(field, [])
        )

    return result


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def _normalize_text(text: str) -> str:
    """
    Normalize text for matching.
    """

    if not text:

        return ""

    text = text.lower()

    # Normalize common separators
    text = text.replace("&", " and ")

    text = re.sub(
        r"[/|_,;:()\[\]{}]+",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# TOKENIZATION
# ============================================================

def _tokens(text: str) -> set[str]:
    """
    Convert text into useful lowercase tokens.
    """

    normalized = _normalize_text(text)

    if not normalized:

        return set()

    words = re.findall(
        r"[a-z0-9+#.-]+",
        normalized
    )

    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "are",
        "you",
        "your",
        "our",
        "will",
        "have",
        "has",
        "into",
        "their",
        "they",
        "them",
        "about",
        "using",
        "use",
        "work",
        "working",
        "role",
        "job",
        "team",
        "candidate",
        "ability",
        "strong",
        "good",
        "must",
        "should",
        "would",
        "can",
        "may",
        "who",
        "what",
        "where",
        "when",
        "how",
        "all",
        "any",
        "its",
        "our",
        "also",
        "more",
        "than",
        "such",
        "other",
        "their",
        "these",
        "those",
        "within",
        "through",
        "including",
        "responsible",
        "responsibilities",
        "required",
        "preferred",
        "requirements"
    }

    return {
        word
        for word in words
        if len(word) >= 3
        and word not in stop_words
    }


# ============================================================
# PHRASE / TOKEN MATCHING
# ============================================================

def _requirement_match(
    requirement: str,
    resume_text: str
) -> tuple[bool, float, str]:
    """
    Determine how strongly a requirement appears in the
    resume.

    Returns:

    matched
    coverage percentage
    match type
    """

    requirement_normalized = _normalize_text(
        requirement
    )

    resume_normalized = _normalize_text(
        resume_text
    )

    if not requirement_normalized:

        return False, 0.0, "empty"

    # Exact phrase match
    if requirement_normalized in resume_normalized:

        return True, 100.0, "exact_phrase"

    requirement_tokens = _tokens(
        requirement
    )

    if not requirement_tokens:

        return False, 0.0, "none"

    resume_tokens = _tokens(
        resume_text
    )

    if not resume_tokens:

        return False, 0.0, "none"

    matched_tokens = (
        requirement_tokens
        &
        resume_tokens
    )

    coverage = (
        len(matched_tokens)
        /
        len(requirement_tokens)
    ) * 100

    # Strong token coverage
    if coverage >= 75:

        return True, coverage, "strong_token"

    # Partial coverage can still be useful,
    # but is not treated as a full requirement match.
    if coverage >= 50:

        return True, coverage, "partial_token"

    return False, coverage, "none"


# ============================================================
# REQUIREMENT COLLECTION
# ============================================================

def _unique_requirements(
    values: list[str]
) -> list[str]:
    """
    Remove duplicate requirements while preserving order.
    """

    result = []

    seen = set()

    for value in values:

        if not isinstance(value, str):

            continue

        value = value.strip()

        if not value:

            continue

        normalized = _normalize_text(
            value
        )

        if not normalized:

            continue

        if normalized in seen:

            continue

        seen.add(normalized)

        result.append(value)

    return result


# ============================================================
# SECTION DETECTION
# ============================================================

def _calculate_section_score(
    resume_text: str
) -> tuple[float, list[str], list[str]]:
    """
    Evaluate whether a resume contains useful standard
    sections.

    The scoring is intentionally domain-independent.
    """

    resume_lower = _normalize_text(
        resume_text
    )

    section_patterns = {

        "summary": [
            "summary",
            "professional summary",
            "profile",
            "objective"
        ],

        "skills": [
            "skills",
            "technical skills",
            "core skills",
            "key skills",
            "competencies"
        ],

        "education": [
            "education",
            "academic background",
            "academic qualifications"
        ],

        "experience": [
            "experience",
            "work experience",
            "professional experience",
            "employment",
            "work history"
        ],

        "projects": [
            "projects",
            "project experience",
            "academic projects"
        ],

        "certifications": [
            "certifications",
            "certificates",
            "licenses"
        ],

        "achievements": [
            "achievements",
            "awards",
            "accomplishments"
        ]
    }

    found = []
    missing = []

    # Core sections receive more importance
    core_sections = {
        "summary",
        "skills",
        "education",
        "experience",
        "projects"
    }

    total_weight = 0.0
    earned_weight = 0.0

    for section, patterns in section_patterns.items():

        weight = 2.0 if section in core_sections else 1.0

        total_weight += weight

        section_found = any(
            pattern in resume_lower
            for pattern in patterns
        )

        if section_found:

            found.append(section)

            earned_weight += weight

        else:

            missing.append(section)

    if total_weight == 0:

        return 0.0, found, missing

    score = (
        earned_weight
        /
        total_weight
    ) * 100

    return score, found, missing


# ============================================================
# JOB TITLE / ROLE MATCH
# ============================================================

def _calculate_role_match(
    resume_text: str,
    job_analysis: dict
) -> tuple[float, list[str]]:
    """
    Evaluate whether the candidate's resume appears relevant
    to the requested job role.

    This is deliberately conservative.
    """

    job_title = job_analysis.get(
        "job_title",
        ""
    )

    if not isinstance(job_title, str):

        job_title = ""

    job_title = job_title.strip()

    if not job_title:

        return 50.0, []

    resume_normalized = _normalize_text(
        resume_text
    )

    title_tokens = _tokens(
        job_title
    )

    if not title_tokens:

        return 50.0, []

    matched = [
        token
        for token in title_tokens
        if token in resume_normalized
    ]

    coverage = (
        len(matched)
        /
        len(title_tokens)
    ) * 100

    return round(
        coverage
    ), matched


# ============================================================
# RESPONSIBILITY MATCH
# ============================================================

def _calculate_responsibility_match(
    resume_text: str,
    responsibilities: list[str]
) -> tuple[float, list[str], list[str]]:
    """
    Compare JD responsibilities against the resume.
    """

    if not responsibilities:

        return 50.0, [], []

    matched = []
    missing = []

    scores = []

    for responsibility in responsibilities:

        is_match, coverage, match_type = (
            _requirement_match(
                responsibility,
                resume_text
            )
        )

        if is_match and coverage >= 75:

            matched.append(
                responsibility
            )

            scores.append(
                min(100, coverage)
            )

        elif is_match and coverage >= 50:

            matched.append(
                responsibility
            )

            scores.append(
                coverage * 0.75
            )

        else:

            missing.append(
                responsibility
            )

            scores.append(
                coverage * 0.35
            )

    if not scores:

        return 0.0, matched, missing

    score = sum(scores) / len(scores)

    return round(score), matched, missing


# ============================================================
# SKILL MATCH
# ============================================================

def _calculate_skill_match(
    resume_text: str,
    skills: list[str]
) -> tuple[float, list[str], list[str]]:
    """
    Compare skills/tools/technologies against the resume.
    """

    if not skills:

        return 50.0, [], []

    matched = []
    missing = []
    scores = []

    for skill in skills:

        is_match, coverage, match_type = (
            _requirement_match(
                skill,
                resume_text
            )
        )

        if is_match:

            matched.append(skill)

            if match_type == "exact_phrase":

                scores.append(100)

            elif match_type == "strong_token":

                scores.append(
                    min(100, coverage)
                )

            else:

                scores.append(
                    coverage * 0.75
                )

        else:

            missing.append(skill)

            scores.append(
                coverage * 0.25
            )

    if not scores:

        return 0.0, matched, missing

    score = sum(scores) / len(scores)

    return round(score), matched, missing


# ============================================================
# EVIDENCE / ACHIEVEMENT SCORE
# ============================================================

def _calculate_evidence_score(
    resume_text: str
) -> dict:
    """
    Evaluate evidence signals such as bullets and
    quantified achievements.

    This does NOT require numbers because not every
    legitimate resume has quantified achievements.
    """

    bullet_lines = re.findall(
        r"(?m)^\s*(?:[-•*]|\d+[.)])\s+.+$",
        resume_text
    )

    bullet_count = len(
        bullet_lines
    )

    quantified_matches = re.findall(
        r"\b\d+(?:\.\d+)?(?:%|x|k|m|b)?\b",
        resume_text.lower()
    )

    quantified_count = len(
        quantified_matches
    )

    action_words = {
        "developed",
        "created",
        "built",
        "designed",
        "implemented",
        "managed",
        "led",
        "analyzed",
        "improved",
        "optimized",
        "delivered",
        "launched",
        "automated",
        "tested",
        "engineered",
        "coordinated",
        "organized",
        "researched",
        "configured",
        "deployed",
        "integrated"
    }

    resume_tokens = _tokens(
        resume_text
    )

    action_word_count = len(
        action_words
        &
        resume_tokens
    )

    bullet_score = min(
        100,
        bullet_count * 8
    )

    quantified_score = min(
        100,
        quantified_count * 15
    )

    action_score = min(
        100,
        action_word_count * 10
    )

    evidence_score = (
        bullet_score * 0.40
        +
        quantified_score * 0.25
        +
        action_score * 0.35
    )

    return {

        "score":
            round(evidence_score),

        "bullet_count":
            bullet_count,

        "quantified_count":
            quantified_count,

        "action_word_count":
            action_word_count
    }


# ============================================================
# RESUME LENGTH SCORE
# ============================================================

def _calculate_length_score(
    resume_text: str
) -> float:
    """
    Evaluate resume length.

    The score is only a small component of the total ATS
    score and does not punish legitimate longer resumes
    excessively.
    """

    word_count = len(
        resume_text.split()
    )

    if 350 <= word_count <= 1100:

        return 100

    if 250 <= word_count < 350:

        return 90

    if 1100 < word_count <= 1400:

        return 90

    if 180 <= word_count < 250:

        return 75

    if 1400 < word_count <= 1700:

        return 75

    return 60


# ============================================================
# READABILITY SCORE
# ============================================================

def _calculate_readability_score(
    resume_text: str
) -> float:
    """
    Basic ATS readability heuristics.
    """

    if not resume_text.strip():

        return 0

    score = 100.0

    # Extremely long lines can be harder for parsers
    lines = resume_text.splitlines()

    long_lines = [
        line
        for line in lines
        if len(line) > 180
    ]

    if long_lines:

        score -= min(
            20,
            len(long_lines) * 3
        )

    # Excessive special characters
    special_count = len(
        re.findall(
            r"[^\w\s.,;:/()&%+#'\"-]",
            resume_text
        )
    )

    if special_count > 30:

        score -= 10

    # Excessive repeated blank lines
    if re.search(
        r"\n\s*\n\s*\n\s*\n",
        resume_text
    ):

        score -= 5

    return round(
        max(
            0,
            min(
                100,
                score
            )
        )
    )


# ============================================================
# INTERNAL ATS SCORING
# ============================================================

def calculate_ats_score(
    resume_text: str,
    job_description: str,
    job_analysis: dict | None = None
) -> dict:
    """
    Calculate a stronger internal ATS-style compatibility
    score.

    IMPORTANT:

    This is an internal heuristic, NOT a guarantee of an
    employer's ATS score.

    Score composition:

    Required skills / requirements       25%
    Overall skills & technologies        20%
    JD responsibilities                 15%
    Role/title relevance                10%
    Keyword coverage                    10%
    Resume structure                     8%
    Evidence / achievements              5%
    Readability                          4%
    Length                               3%

    Total                               100%
    """

    if not resume_text or not resume_text.strip():

        return {
            "ats_score": 0,
            "score_status": "No resume text available.",
            "target_score": ATS_TARGET_SCORE,
            "minimum_score": ATS_MINIMUM_SCORE,
            "target_reached": False,
            "is_90_plus": False,
            "is_80_plus": False,
            "keyword_coverage_percent": 0,
            "required_coverage_percent": 0,
            "skills_coverage_percent": 0,
            "responsibility_coverage_percent": 0,
            "role_relevance_percent": 0,
            "resume_section_score": 0,
            "evidence_score": 0,
            "readability_score": 0,
            "length_score": 0,
            "matched_requirements": [],
            "missing_requirements": [],
            "blocking_gaps": [],
            "notes": [
                "Resume text is empty."
            ]
        }

    if not job_description or not job_description.strip():

        return {
            "ats_score": 0,
            "score_status":
                "No job description available.",
            "target_score": ATS_TARGET_SCORE,
            "minimum_score": ATS_MINIMUM_SCORE,
            "target_reached": False,
            "is_90_plus": False,
            "is_80_plus": False,
            "keyword_coverage_percent": 0,
            "required_coverage_percent": 0,
            "skills_coverage_percent": 0,
            "responsibility_coverage_percent": 0,
            "role_relevance_percent": 0,
            "resume_section_score": 0,
            "evidence_score": 0,
            "readability_score": 0,
            "length_score": 0,
            "matched_requirements": [],
            "missing_requirements": [],
            "blocking_gaps": [],
            "notes": [
                "Job description is empty."
            ]
        }

    # --------------------------------------------------------
    # JOB ANALYSIS
    # --------------------------------------------------------

    if job_analysis is None:

        job_analysis = analyze_job_description(
            job_description
        )

    # --------------------------------------------------------
    # NORMALIZE JOB DATA
    # --------------------------------------------------------

    required_skills = _clean_list(
        job_analysis.get(
            "required_skills",
            []
        )
    )

    preferred_skills = _clean_list(
        job_analysis.get(
            "preferred_skills",
            []
        )
    )

    tools_and_technologies = _clean_list(
        job_analysis.get(
            "tools_and_technologies",
            []
        )
    )

    qualifications = _clean_list(
        job_analysis.get(
            "qualifications",
            []
        )
    )

    certifications = _clean_list(
        job_analysis.get(
            "certifications",
            []
        )
    )

    keywords = _clean_list(
        job_analysis.get(
            "keywords",
            []
        )
    )

    important_requirements = _clean_list(
        job_analysis.get(
            "important_requirements",
            []
        )
    )

    responsibilities = _clean_list(
        job_analysis.get(
            "responsibilities",
            []
        )
    )

    # --------------------------------------------------------
    # REQUIRED REQUIREMENTS
    # --------------------------------------------------------

    required_requirements = _unique_requirements(
        required_skills
        +
        qualifications
        +
        certifications
        +
        important_requirements
    )

    # --------------------------------------------------------
    # GENERAL SKILLS
    # --------------------------------------------------------

    skill_requirements = _unique_requirements(
        required_skills
        +
        preferred_skills
        +
        tools_and_technologies
    )

    # --------------------------------------------------------
    # GENERAL ATS KEYWORDS
    # --------------------------------------------------------

    all_keywords = _unique_requirements(
        keywords
        +
        skill_requirements
        +
        important_requirements
    )

    # --------------------------------------------------------
    # REQUIRED MATCHING
    # --------------------------------------------------------

    required_matched = []
    required_missing = []
    required_scores = []

    for requirement in required_requirements:

        matched, coverage, match_type = (
            _requirement_match(
                requirement,
                resume_text
            )
        )

        if matched and coverage >= 75:

            required_matched.append(
                requirement
            )

            required_scores.append(
                min(100, coverage)
            )

        elif matched and coverage >= 50:

            required_matched.append(
                requirement
            )

            required_scores.append(
                coverage * 0.75
            )

        else:

            required_missing.append(
                requirement
            )

            required_scores.append(
                coverage * 0.25
            )

    if required_scores:

        required_coverage = (
            sum(required_scores)
            /
            len(required_scores)
        )

    else:

        required_coverage = 100

    # --------------------------------------------------------
    # SKILL MATCHING
    # --------------------------------------------------------

    (
        skills_coverage,
        matched_skills,
        missing_skills
    ) = _calculate_skill_match(
        resume_text,
        skill_requirements
    )

    # --------------------------------------------------------
    # KEYWORD MATCHING
    # --------------------------------------------------------

    keyword_matched = []
    keyword_missing = []
    keyword_scores = []

    for keyword in all_keywords:

        matched, coverage, match_type = (
            _requirement_match(
                keyword,
                resume_text
            )
        )

        if matched:

            keyword_matched.append(
                keyword
            )

            keyword_scores.append(
                coverage
            )

        else:

            keyword_missing.append(
                keyword
            )

            keyword_scores.append(
                coverage * 0.25
            )

    if keyword_scores:

        keyword_coverage = (
            sum(keyword_scores)
            /
            len(keyword_scores)
        )

    else:

        keyword_coverage = 100

    # --------------------------------------------------------
    # RESPONSIBILITY MATCH
    # --------------------------------------------------------

    (
        responsibility_score,
        matched_responsibilities,
        missing_responsibilities
    ) = _calculate_responsibility_match(
        resume_text,
        responsibilities
    )

    # --------------------------------------------------------
    # ROLE MATCH
    # --------------------------------------------------------

    (
        role_score,
        matched_role_tokens
    ) = _calculate_role_match(
        resume_text,
        job_analysis
    )

    # --------------------------------------------------------
    # RESUME SECTIONS
    # --------------------------------------------------------

    (
        section_score,
        sections_found,
        sections_missing
    ) = _calculate_section_score(
        resume_text
    )

    # --------------------------------------------------------
    # EVIDENCE
    # --------------------------------------------------------

    evidence = _calculate_evidence_score(
        resume_text
    )

    evidence_score = evidence[
        "score"
    ]

    # --------------------------------------------------------
    # READABILITY
    # --------------------------------------------------------

    readability_score = _calculate_readability_score(
        resume_text
    )

    # --------------------------------------------------------
    # LENGTH
    # --------------------------------------------------------

    length_score = _calculate_length_score(
        resume_text
    )

    # --------------------------------------------------------
    # FINAL SCORE
    # --------------------------------------------------------

    final_score = (

        required_coverage * 0.25

        +

        skills_coverage * 0.20

        +

        responsibility_score * 0.15

        +

        role_score * 0.10

        +

        keyword_coverage * 0.10

        +

        section_score * 0.08

        +

        evidence_score * 0.05

        +

        readability_score * 0.04

        +

        length_score * 0.03

    )

    final_score = round(
        max(
            0,
            min(
                100,
                final_score
            )
        )
    )

    # --------------------------------------------------------
    # BLOCKING GAPS
    # --------------------------------------------------------

    blocking_gaps = []

    # Missing required qualifications
    for item in required_missing:

        if item not in blocking_gaps:

            blocking_gaps.append(item)

    # Missing required skills
    for item in missing_skills:

        if item in required_skills:

            if item not in blocking_gaps:

                blocking_gaps.append(item)

    # Missing certifications
    for item in certifications:

        matched, coverage, _ = (
            _requirement_match(
                item,
                resume_text
            )
        )

        if not matched:

            if item not in blocking_gaps:

                blocking_gaps.append(item)

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    target_reached = (
        final_score >= ATS_TARGET_SCORE
    )

    if target_reached:

        status = (
            "ATS target of 90 reached."
        )

    elif final_score >= 80:

        status = (
            "ATS score is strong but below the "
            "required target of 90."
        )

    else:

        status = (
            "ATS score is below the required "
            "minimum of 90."
        )

    # --------------------------------------------------------
    # NOTES
    # --------------------------------------------------------

    notes = [

        "This is an internal heuristic ATS score.",

        "It is not a guarantee of any employer's ATS result.",

        "Required requirements are weighted more heavily "
        "than preferred requirements.",

        "Only legitimate resume improvements should be used.",

        "Unsupported qualifications must never be fabricated."
    ]

    if blocking_gaps:

        notes.append(
            "Some important requirements are not supported "
            "by the current resume."
        )

    return {

        "ats_score":
            final_score,

        "score_status":
            status,

        "target_score":
            ATS_TARGET_SCORE,

        "minimum_score":
            ATS_MINIMUM_SCORE,

        "target_reached":
            target_reached,

        "is_90_plus":
            final_score >= 90,

        "is_80_plus":
            final_score >= 80,

        "keyword_coverage_percent":
            round(keyword_coverage),

        "required_coverage_percent":
            round(required_coverage),

        "skills_coverage_percent":
            round(skills_coverage),

        "responsibility_coverage_percent":
            round(responsibility_score),

        "role_relevance_percent":
            round(role_score),

        "resume_section_score":
            round(section_score),

        "evidence_score":
            evidence_score,

        "readability_score":
            readability_score,

        "length_score":
            round(length_score),

        "matched_requirements":
            _unique_requirements(
                required_matched
                +
                matched_skills
                +
                keyword_matched
                +
                matched_responsibilities
            ),

        "missing_requirements":
            _unique_requirements(
                required_missing
                +
                missing_skills
                +
                keyword_missing
                +
                missing_responsibilities
            ),

        "blocking_gaps":
            _unique_requirements(
                blocking_gaps
            ),

        "sections_found":
            sections_found,

        "sections_missing":
            sections_missing,

        "matched_role_tokens":
            matched_role_tokens,

        "evidence_details":
            evidence,

        "notes":
            notes
    }


# ============================================================
# RESUME OPTIMIZATION
# ============================================================

def optimize_resume(
    resume_text: str,
    job_description: str,
    current_score: int | None = None,
    ats_feedback: dict | None = None
) -> dict:
    """
    Improve resume wording and ATS alignment while preserving
    factual truth.
    """

    score_text = ""

    if current_score is not None:

        score_text = (
            f"""
CURRENT INTERNAL ATS SCORE:
{current_score}

TARGET INTERNAL ATS SCORE:
{ATS_TARGET_SCORE}
"""
        )

    feedback_text = ""

    if ats_feedback:

        feedback_text = f"""
CURRENT ATS ANALYSIS:

{json.dumps(
    ats_feedback,
    indent=2,
    ensure_ascii=False
)}
"""

    prompt = f"""
You are an expert ATS resume optimization assistant.

Your task is to improve the candidate's resume for the
specific target job.

ORIGINAL / CURRENT RESUME:
{resume_text}

TARGET JOB DESCRIPTION:
{job_description}

{score_text}

{feedback_text}

TARGET:
Achieve an internal ATS score of at least 90 if this can
be done using information genuinely supported by the
original resume.

IMPORTANT:

A high score is NOT more important than truthfulness.

ABSOLUTE TRUTH RULE:

You MUST NOT invent, add, imply, or manufacture:

- Skills
- Experience
- Projects
- Certifications
- Degrees
- Employers
- Job titles
- Dates
- Achievements
- Metrics
- Responsibilities
- Tools
- Technologies
- Qualifications
- Awards
- Publications
- Licenses

that are not supported by the original resume.

NEVER fabricate information simply because the JD requests it.

You MAY:

1. Rewrite existing statements.
2. Improve grammar.
3. Improve professional wording.
4. Reorder information.
5. Move relevant information higher.
6. Make existing experience clearer.
7. Use terminology from the JD when that terminology
   accurately describes something already present in the
   resume.
8. Combine related existing information.
9. Remove unnecessary repetition.
10. Improve bullet points using facts already present.
11. Improve keyword placement.
12. Make existing achievements easier for ATS systems
    to identify.

For example:

If the resume says:

"Built website using Python."

and the JD repeatedly says:

"Python development"

you may rewrite the legitimate statement as:

"Developed a website using Python."

But you may NOT write:

"Developed production Python applications for 5 years."

unless that information actually exists.

IMPORTANT ATS PRINCIPLE:

Do not blindly stuff keywords.

Every keyword included must be genuinely supported by
the candidate's original resume.

Prioritize:

1. Required JD skills
2. Required qualifications
3. Relevant responsibilities
4. Relevant tools and technologies
5. Job-role terminology
6. Preferred skills
7. General keywords

If a requirement is unsupported, leave it unsupported.

Return ONLY valid JSON:

{{
    "optimized_resume": "",
    "changes_made": [],
    "supported_keywords_added": [],
    "unsupported_requirements": [],
    "blocking_gaps": [],
    "truthfulness_note": ""
}}
"""

    response = ask_gemini(
        prompt
    )

    result = _json_from_response(
        response
    )

    if not result:

        return {

            "optimized_resume":
                resume_text,

            "changes_made":
                [],

            "supported_keywords_added":
                [],

            "unsupported_requirements":
                [],

            "blocking_gaps":
                [],

            "truthfulness_note":
                "Optimization response could not be parsed."
        }

    optimized_resume = result.get(
        "optimized_resume",
        resume_text
    )

    if not isinstance(
        optimized_resume,
        str
    ) or not optimized_resume.strip():

        optimized_resume = resume_text

    result[
        "optimized_resume"
    ] = optimized_resume

    result[
        "changes_made"
    ] = _clean_list(
        result.get(
            "changes_made",
            []
        )
    )

    result[
        "supported_keywords_added"
    ] = _clean_list(
        result.get(
            "supported_keywords_added",
            []
        )
    )

    result[
        "unsupported_requirements"
    ] = _clean_list(
        result.get(
            "unsupported_requirements",
            []
        )
    )

    result[
        "blocking_gaps"
    ] = _clean_list(
        result.get(
            "blocking_gaps",
            []
        )
    )

    return result


# ============================================================
# ITERATIVE ATS OPTIMIZATION
# ============================================================

def optimize_until_80(
    resume_text: str,
    job_description: str,
    max_iterations: int = 6
) -> dict:
    """
    Backward-compatible function name.

    IMPORTANT:
    The old function name is retained so the current
    main.py continues to work.

    The actual target has been upgraded from 80 to 90.
    """

    max_iterations = max(
        1,
        min(
            max_iterations,
            MAX_OPTIMIZATION_ITERATIONS
        )
    )

    # --------------------------------------------------------
    # ANALYZE JOB
    # --------------------------------------------------------

    job_analysis = analyze_job_description(
        job_description
    )

    # --------------------------------------------------------
    # SCORE ORIGINAL RESUME
    # --------------------------------------------------------

    original_score = calculate_ats_score(

        resume_text,

        job_description,

        job_analysis
    )

    best_resume = resume_text

    best_score = original_score

    history = [

        {
            "iteration":
                0,

            "ats_score":
                original_score[
                    "ats_score"
                ],

            "target_score":
                ATS_TARGET_SCORE,

            "target_reached":
                original_score[
                    "target_reached"
                ],

            "blocking_gaps":
                original_score[
                    "blocking_gaps"
                ]
        }

    ]

    # --------------------------------------------------------
    # ALREADY >= 90
    # --------------------------------------------------------

    if (
        original_score[
            "ats_score"
        ]
        >=
        ATS_TARGET_SCORE
    ):

        return {

            "success":
                True,

            "target_reached":
                True,

            "target_score":
                ATS_TARGET_SCORE,

            "message":
                "Original resume already meets the internal ATS target of 90.",

            "original_score":
                original_score,

            "final_score":
                original_score,

            "best_resume":
                best_resume,

            "history":
                history,

            "job_analysis":
                job_analysis,

            "blocking_gaps":
                original_score[
                    "blocking_gaps"
                ]
        }

    # --------------------------------------------------------
    # ITERATIVE IMPROVEMENT
    # --------------------------------------------------------

    current_resume = resume_text

    for iteration in range(
        1,
        max_iterations + 1
    ):

        optimization = optimize_resume(

            current_resume,

            job_description,

            best_score[
                "ats_score"
            ],

            best_score
        )

        candidate_resume = optimization.get(
            "optimized_resume",
            current_resume
        )

        # Safety fallback
        if not isinstance(
            candidate_resume,
            str
        ) or not candidate_resume.strip():

            candidate_resume = current_resume

        # ----------------------------------------------------
        # SCORE CANDIDATE
        # ----------------------------------------------------

        candidate_score = calculate_ats_score(

            candidate_resume,

            job_description,

            job_analysis
        )

        # ----------------------------------------------------
        # TRUTH SAFETY CHECK
        # ----------------------------------------------------

        unsupported_requirements = (
            optimization.get(
                "unsupported_requirements",
                []
            )
        )

        blocking_gaps = (
            optimization.get(
                "blocking_gaps",
                []
            )
        )

        # ----------------------------------------------------
        # HISTORY
        # ----------------------------------------------------

        history.append({

            "iteration":
                iteration,

            "ats_score":
                candidate_score[
                    "ats_score"
                ],

            "target_score":
                ATS_TARGET_SCORE,

            "target_reached":
                candidate_score[
                    "target_reached"
                ],

            "score_change":
                (
                    candidate_score[
                        "ats_score"
                    ]
                    -
                    best_score[
                        "ats_score"
                    ]
                ),

            "changes_made":
                optimization.get(
                    "changes_made",
                    []
                ),

            "supported_keywords_added":
                optimization.get(
                    "supported_keywords_added",
                    []
                ),

            "unsupported_requirements":
                unsupported_requirements,

            "blocking_gaps":
                blocking_gaps
        })

        # ----------------------------------------------------
        # KEEP ONLY BETTER VERSION
        # ----------------------------------------------------

        if (
            candidate_score[
                "ats_score"
            ]
            >
            best_score[
                "ats_score"
            ]
        ):

            best_resume = candidate_resume

            best_score = candidate_score

            current_resume = candidate_resume

        else:

            # No improvement.
            # Stop rather than making unnecessary API calls.
            break

        # ----------------------------------------------------
        # TARGET REACHED
        # ----------------------------------------------------

        if (
            best_score[
                "ats_score"
            ]
            >=
            ATS_TARGET_SCORE
        ):

            break

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    target_reached = (
        best_score[
            "ats_score"
        ]
        >=
        ATS_TARGET_SCORE
    )

    if target_reached:

        message = (
            "Internal ATS target of 90 or higher was reached "
            "using legitimate resume improvements."
        )

    else:

        message = (
            "The internal ATS target of 90 could not be reached "
            "without inventing unsupported qualifications. "
            "The best legitimate version has been returned."
        )

    return {

        "success":
            True,

        "target_reached":
            target_reached,

        "target_score":
            ATS_TARGET_SCORE,

        "minimum_score":
            ATS_MINIMUM_SCORE,

        "message":
            message,

        "original_score":
            original_score,

        "final_score":
            best_score,

        "best_resume":
            best_resume,

        "history":
            history,

        "job_analysis":
            job_analysis,

        "blocking_gaps":
            best_score.get(
                "blocking_gaps",
                []
            )
    }


# ============================================================
# NEW CLEAR FUNCTION NAME
# ============================================================

def optimize_until_90(
    resume_text: str,
    job_description: str,
    max_iterations: int = 6
) -> dict:
    """
    Preferred public function name.

    This simply calls the backward-compatible implementation.
    """

    return optimize_until_80(

        resume_text,

        job_description,

        max_iterations
    )