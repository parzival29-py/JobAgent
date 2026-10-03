import re


# ============================================================
# SECTION ALIASES
# ============================================================

SECTION_ALIASES = {
    "summary": [
        "summary",
        "professional summary",
        "profile",
        "career objective",
        "objective",
        "about me"
    ],

    "skills": [
        "skills",
        "technical skills",
        "core skills",
        "key skills",
        "competencies",
        "areas of expertise"
    ],

    "education": [
        "education",
        "academic background",
        "academic qualifications",
        "qualifications"
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
        "academic projects",
        "personal projects",
        "project experience"
    ],

    "certifications": [
        "certifications",
        "certificates",
        "licenses"
    ],

    "achievements": [
        "achievements",
        "accomplishments",
        "awards",
        "honors"
    ],

    "publications": [
        "publications",
        "research",
        "papers"
    ]
}


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text: str) -> str:
    """
    Clean extracted resume text while preserving useful
    information.
    """

    if not text:
        return ""

    # Normalize line endings
    text = text.replace(
        "\r\n",
        "\n"
    ).replace(
        "\r",
        "\n"
    )

    # Replace tabs with spaces
    text = text.replace(
        "\t",
        " "
    )

    # Remove excessive spaces
    text = re.sub(
        r"[ ]{2,}",
        " ",
        text
    )

    # Remove excessive blank lines
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# EMAIL EXTRACTION
# ============================================================

def extract_email(text: str) -> str:
    """
    Extract the first email address from resume text.
    """

    if not text:
        return ""

    match = re.search(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        text
    )

    if match:

        return match.group(0)

    return ""


# ============================================================
# PHONE EXTRACTION
# ============================================================

def extract_phone(text: str) -> str:
    """
    Extract a likely phone number.

    Supports common international and Indian formats.
    """

    if not text:
        return ""

    patterns = [

        r"\+91[\s-]?\d{5}[\s-]?\d{5}",

        r"\+91[\s-]?\d{10}",

        r"\b\d{10}\b",

        r"\b\d{3}[\s-]\d{3}[\s-]\d{4}\b",

        r"\b\d{4}[\s-]\d{3}[\s-]\d{3}\b"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            return match.group(0).strip()

    return ""


# ============================================================
# NAME EXTRACTION
# ============================================================

def extract_name(text: str) -> str:
    """
    Attempt to identify the candidate's name.

    Usually the first meaningful line of a resume is
    the candidate's name.
    """

    if not text:
        return ""

    lines = [

        line.strip()

        for line in text.splitlines()

        if line.strip()
    ]

    if not lines:

        return ""

    # Ignore obvious headings/contact information
    ignored_words = {
        "resume",
        "cv",
        "curriculum vitae",
        "profile",
        "summary",
        "objective",
        "experience",
        "education",
        "skills"
    }

    for line in lines[:10]:

        lower_line = line.lower()

        if lower_line in ignored_words:

            continue

        if "@" in line:

            continue

        if re.search(
            r"\d{5,}",
            line
        ):

            continue

        # Avoid very long sentences
        if len(line.split()) > 6:

            continue

        # Name-like line
        if re.fullmatch(
            r"[A-Za-z][A-Za-z .'-]{1,60}",
            line
        ):

            return line

    return lines[0]


# ============================================================
# HEADING DETECTION
# ============================================================

def _is_heading(
    line: str,
    known_headings: set[str]
) -> bool:
    """
    Determine whether a line is probably a resume section
    heading.
    """

    cleaned = line.strip()

    if not cleaned:

        return False

    normalized = re.sub(
        r"[:\-]+$",
        "",
        cleaned.lower()
    ).strip()

    if normalized in known_headings:

        return True

    # Uppercase headings such as:
    # EDUCATION
    # EXPERIENCE
    # PROJECTS

    if (
        cleaned.upper() == cleaned
        and len(cleaned.split()) <= 5
        and any(
            character.isalpha()
            for character in cleaned
        )
    ):

        return True

    return False


# ============================================================
# SINGLE SECTION EXTRACTION
# ============================================================

def extract_section(
    text: str,
    section_name: str
) -> str:
    """
    Extract one logical resume section.
    """

    aliases = SECTION_ALIASES.get(
        section_name,
        []
    )

    if not aliases:

        return ""

    lines = text.splitlines()

    known_headings = {

        alias.lower()

        for values in SECTION_ALIASES.values()

        for alias in values
    }

    current_section = None

    collected = []

    for line in lines:

        stripped = line.strip()

        if not stripped:

            continue

        normalized = re.sub(
            r"[:\-]+$",
            "",
            stripped.lower()
        ).strip()

        # Check whether this is a known heading
        if _is_heading(
            stripped,
            known_headings
        ):

            current_section = None

            for possible_section, values in SECTION_ALIASES.items():

                if normalized in [
                    value.lower()
                    for value in values
                ]:

                    current_section = possible_section

                    break

            continue

        if current_section == section_name:

            collected.append(
                stripped
            )

    return "\n".join(
        collected
    ).strip()


# ============================================================
# EXTRACT ALL SECTIONS
# ============================================================

def extract_all_sections(
    text: str
) -> dict:
    """
    Extract all recognized resume sections.
    """

    sections = {}

    for section_name in SECTION_ALIASES:

        sections[section_name] = extract_section(
            text,
            section_name
        )

    return sections


# ============================================================
# GENERIC KEYWORD EXTRACTION
# ============================================================

def extract_keywords(
    text: str,
    limit: int = 80
) -> list[str]:
    """
    Extract frequently occurring useful terms.

    This intentionally does NOT use a fixed career-domain
    dictionary. It can therefore work with resumes from
    many different fields.
    """

    if not text:
        return []

    words = re.findall(
        r"[A-Za-z][A-Za-z0-9+#./-]{2,}",
        text.lower()
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
        "was",
        "were",
        "been",
        "have",
        "has",
        "had",
        "will",
        "would",
        "could",
        "should",
        "can",
        "may",
        "into",
        "using",
        "used",
        "use",
        "their",
        "there",
        "they",
        "them",
        "your",
        "you",
        "our",
        "about",
        "also",
        "more",
        "than",
        "then",
        "such",
        "other",
        "through",
        "within",
        "while",
        "where",
        "which",
        "whose",
        "each",
        "both",
        "very",
        "work",
        "working",
        "worked",
        "role",
        "roles",
        "team",
        "teams",
        "job",
        "jobs",
        "company",
        "candidate",
        "experience",
        "years",
        "year"
    }

    frequency = {}

    for word in words:

        if word in stop_words:

            continue

        if len(word) < 3:

            continue

        frequency[word] = (
            frequency.get(
                word,
                0
            ) + 1
        )

    sorted_words = sorted(
        frequency.items(),
        key=lambda item: (
            -item[1],
            item[0]
        )
    )

    return [
        word
        for word, _ in sorted_words[:limit]
    ]


# ============================================================
# BUILD STRUCTURED PROFILE
# ============================================================

def build_profile(
    text: str
) -> dict:
    """
    Convert raw resume text into a general-purpose
    structured profile.

    This function intentionally avoids assuming a particular
    academic or professional domain.
    """

    cleaned = clean_text(
        text
    )

    sections = extract_all_sections(
        cleaned
    )

    profile = {

        "name":
            extract_name(cleaned),

        "email":
            extract_email(cleaned),

        "phone":
            extract_phone(cleaned),

        "summary":
            sections.get(
                "summary",
                ""
            ),

        "skills":
            sections.get(
                "skills",
                ""
            ),

        "education":
            sections.get(
                "education",
                ""
            ),

        "experience":
            sections.get(
                "experience",
                ""
            ),

        "projects":
            sections.get(
                "projects",
                ""
            ),

        "certifications":
            sections.get(
                "certifications",
                ""
            ),

        "achievements":
            sections.get(
                "achievements",
                ""
            ),

        "publications":
            sections.get(
                "publications",
                ""
            ),

        "keywords":
            extract_keywords(
                cleaned
            )
    }

    return profile