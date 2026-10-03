import json
import re

from backend.ai import ask_gemini


# ============================================================
# HELPERS
# ============================================================

def _json_from_response(response):
    """
    Extract JSON from an AI response.
    """

    if isinstance(response, dict):
        return response

    if not response:
        return {}

    text = str(response).strip()

    # Remove markdown code fences
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    try:

        return json.loads(text)

    except json.JSONDecodeError:

        # Try to locate the JSON object
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:

            try:

                return json.loads(
                    text[start:end + 1]
                )

            except json.JSONDecodeError:

                pass

    return {}


def _profile_to_text(profile) -> str:
    """
    Convert the structured resume profile into safe text
    for the AI.

    No information is added.
    """

    if isinstance(profile, str):

        return profile

    if not isinstance(profile, dict):

        return str(profile)

    parts = []

    for key, value in profile.items():

        if value is None:
            continue

        if isinstance(value, list):

            value = "\n".join(
                str(item)
                for item in value
            )

        elif isinstance(value, dict):

            value = json.dumps(
                value,
                ensure_ascii=False
            )

        parts.append(
            f"{key}: {value}"
        )

    return "\n".join(parts)


def _requires_human_confirmation(
    question: str
) -> bool:
    """
    Detect questions that should never be automatically
    answered because they may involve legal, demographic,
    eligibility, or declaration information.
    """

    question_lower = question.lower()

    sensitive_patterns = [

        # Work authorization
        "work authorization",
        "authorized to work",
        "legally authorized",
        "right to work",
        "work permit",
        "visa",
        "sponsorship",
        "visa sponsorship",

        # Legal declarations
        "legal declaration",
        "declare",
        "declaration",
        "certify that",
        "certification that",
        "terms and conditions",

        # Criminal / legal
        "criminal record",
        "criminal history",
        "convicted",
        "felony",
        "misdemeanor",
        "lawsuit",
        "legal proceedings",

        # Demographic information
        "gender",
        "sex",
        "race",
        "ethnicity",
        "religion",
        "disability",
        "veteran",
        "date of birth",
        "marital status",

        # Citizenship
        "citizenship",
        "nationality",
        "passport",

        # Government / identity
        "government id",
        "aadhaar",
        "pan number",
        "social security",
        "tax identification"
    ]

    return any(
        pattern in question_lower
        for pattern in sensitive_patterns
    )


# ============================================================
# COVER LETTER
# ============================================================

def generate_cover_letter(
    profile,
    job_description: str,
    company: str = "",
    job_title: str = ""
):
    """
    Generate a truthful, job-specific cover letter.

    The AI is explicitly instructed not to invent experience,
    skills, achievements, employers, metrics, education,
    certifications, or other facts.
    """

    resume_text = _profile_to_text(
        profile
    )

    company_text = (
        company.strip()
        if company
        else "the company"
    )

    job_title_text = (
        job_title.strip()
        if job_title
        else "the position"
    )

    prompt = f"""
You are a professional job application assistant.

Create a concise, professional cover letter for:

Company:
{company_text}

Position:
{job_title_text}

JOB DESCRIPTION:
{job_description}

CANDIDATE RESUME / PROFILE:
{resume_text}

STRICT RULES:

1. Use ONLY information supported by the candidate profile.
2. NEVER invent skills.
3. NEVER invent experience.
4. NEVER invent projects.
5. NEVER invent achievements.
6. NEVER invent certifications.
7. NEVER invent employers.
8. NEVER invent dates.
9. NEVER invent numerical results or metrics.
10. Do not claim the candidate has a requirement if the profile
    does not support it.
11. Highlight genuine overlaps between the resume and the job.
12. If an important requirement is missing from the resume, do
    not pretend the candidate has it.
13. Keep the letter concise and professional.
14. Do not use fake placeholders such as [Company Name].
15. Do not mention that you are an AI.

Return ONLY the cover letter text.
"""

    response = ask_gemini(
        prompt
    )

    return response


# ============================================================
# APPLICATION QUESTION ANALYSIS
# ============================================================

def analyze_application_question(
    question: str,
    job_description: str = ""
):
    """
    Analyze an application question and determine whether it
    can safely be answered from resume/job context.
    """

    question = question.strip()

    if not question:

        return {

            "question":
                question,

            "requires_human_confirmation":
                False,

            "category":
                "unknown",

            "reason":
                "Question is empty."
        }

    if _requires_human_confirmation(
        question
    ):

        return {

            "question":
                question,

            "requires_human_confirmation":
                True,

            "category":
                "sensitive_or_legal",

            "reason":
                "This question may require personal, legal, "
                "eligibility, demographic, citizenship, or "
                "declaration information. The user should "
                "answer it personally."
        }

    prompt = f"""
Analyze this job application question.

QUESTION:
{question}

JOB DESCRIPTION:
{job_description}

Determine:

1. What category the question belongs to.
2. What information is needed to answer it.
3. Whether it can reasonably be answered using a resume/profile.
4. Whether human confirmation is recommended.

Return ONLY valid JSON:

{{
    "category": "...",
    "information_needed": ["..."],
    "resume_based": true,
    "requires_human_confirmation": false,
    "reason": "..."
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

            "question":
                question,

            "requires_human_confirmation":
                False,

            "category":
                "general",

            "information_needed":
                [],

            "resume_based":
                True,

            "reason":
                "AI analysis did not return structured data."
        }

    result["question"] = question

    return result


# ============================================================
# SINGLE APPLICATION ANSWER
# ============================================================

def generate_application_answer(
    profile,
    question: str,
    job_description: str = ""
):
    """
    Generate an answer to a normal application question.

    Sensitive/legal questions are not automatically answered.
    """

    question = question.strip()

    if not question:

        return {

            "answer":
                "",

            "requires_human_confirmation":
                False,

            "reason":
                "Question is empty."
        }

    if _requires_human_confirmation(
        question
    ):

        return {

            "answer":
                "",

            "requires_human_confirmation":
                True,

            "reason":
                "This question requires information that "
                "should be confirmed and provided by the user."
        }

    resume_text = _profile_to_text(
        profile
    )

    prompt = f"""
You are assisting a candidate with a job application.

JOB DESCRIPTION:
{job_description}

CANDIDATE PROFILE:
{resume_text}

APPLICATION QUESTION:
{question}

Rules:

1. Answer using only information supported by the profile.
2. Never invent facts.
3. Never invent experience.
4. Never invent skills.
5. Never invent projects.
6. Never invent achievements.
7. Never invent employers.
8. Never invent dates.
9. Never invent metrics.
10. Do not claim qualifications that are not supported.
11. If the profile does not contain enough information, clearly
    say that the user needs to provide the missing information.
12. Keep the answer appropriate for a job application.
13. Do not mention that you are an AI.

Return ONLY valid JSON:

{{
    "answer": "...",
    "confidence": "high|medium|low",
    "missing_information": []
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

            "answer":
                str(response),

            "confidence":
                "low",

            "missing_information":
                [],

            "requires_human_confirmation":
                False
        }

    result[
        "requires_human_confirmation"
    ] = False

    return result


# ============================================================
# MULTIPLE APPLICATION ANSWERS
# ============================================================

def generate_application_answers(
    profile,
    questions: list[str],
    job_description: str = ""
):
    """
    Generate answers for multiple application questions.
    """

    results = []

    for question in questions:

        question = str(
            question
        ).strip()

        if not question:

            continue

        analysis = analyze_application_question(

            question,

            job_description
        )

        if analysis.get(
            "requires_human_confirmation",
            False
        ):

            results.append({

                "question":
                    question,

                "answer":
                    "",

                "requires_human_confirmation":
                    True,

                "reason":
                    analysis.get(
                        "reason",
                        "Human confirmation required."
                    )
            })

            continue

        answer = generate_application_answer(

            profile,

            question,

            job_description
        )

        if isinstance(
            answer,
            dict
        ):

            result = {

                "question":
                    question,

                **answer
            }

        else:

            result = {

                "question":
                    question,

                "answer":
                    str(answer),

                "requires_human_confirmation":
                    False
            }

        results.append(
            result
        )

    return results