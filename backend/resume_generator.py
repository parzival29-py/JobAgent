from pathlib import Path
from datetime import datetime
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


# ============================================================
# DIRECTORIES
# ============================================================

UPLOAD_DIR = Path("uploads")
OPTIMIZED_DIR = UPLOAD_DIR / "optimized"

UPLOAD_DIR.mkdir(exist_ok=True)
OPTIMIZED_DIR.mkdir(exist_ok=True)


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value) -> str:
    """
    Convert a value into clean text.
    """

    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    return value.strip()


def split_resume_sections(resume_text: str) -> dict:
    """
    Attempt to identify common resume sections from optimized
    resume text.

    This is domain-independent.
    """

    section_aliases = {

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
        ],

        "publications": [
            "publications",
            "research",
            "papers"
        ]
    }

    lines = [
        line.strip()
        for line in resume_text.splitlines()
        if line.strip()
    ]

    sections = {
        "header": [],
        "summary": [],
        "skills": [],
        "education": [],
        "experience": [],
        "projects": [],
        "certifications": [],
        "achievements": [],
        "publications": [],
        "other": []
    }

    current_section = "header"

    for line in lines:

        normalized = (
            line
            .lower()
            .strip()
            .rstrip(":")
        )

        detected_section = None

        for section, aliases in section_aliases.items():

            if normalized in aliases:

                detected_section = section
                break

        if detected_section:

            current_section = detected_section
            continue

        sections[current_section].append(line)

    return sections


# ============================================================
# DOCUMENT STYLE
# ============================================================

def set_cell_border(cell, **kwargs):
    """
    Set borders on a table cell.
    """

    tc = cell._tc

    tcPr = tc.get_or_add_tcPr()

    tcBorders = tcPr.first_child_found_in(
        "w:tcBorders"
    )

    if tcBorders is None:

        tcBorders = OxmlElement(
            "w:tcBorders"
        )

        tcPr.append(tcBorders)

    for edge in (
        "top",
        "left",
        "bottom",
        "right",
        "insideH",
        "insideV"
    ):

        if edge in kwargs:

            edge_data = kwargs.get(
                edge
            )

            tag = "w:{}".format(
                edge
            )

            element = tcBorders.find(
                qn(tag)
            )

            if element is None:

                element = OxmlElement(
                    tag
                )

                tcBorders.append(
                    element
                )

            for key in [
                "val",
                "sz",
                "space",
                "color"
            ]:

                if key in edge_data:

                    element.set(
                        qn(
                            "w:{}".format(
                                key
                            )
                        ),
                        str(
                            edge_data[key]
                        )
                    )


def configure_document(document: Document):
    """
    Configure professional ATS-friendly document settings.
    """

    section = document.sections[0]

    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.55)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)

    styles = document.styles

    normal = styles["Normal"]

    normal.font.name = "Arial"
    normal.font.size = Pt(9.5)

    # Ensure East Asian font mapping also uses Arial
    normal._element.rPr.rFonts.set(
        qn("w:eastAsia"),
        "Arial"
    )

    normal.paragraph_format.space_after = Pt(2)
    normal.paragraph_format.line_spacing = 1.0


# ============================================================
# HEADING
# ============================================================

def add_section_heading(
    document: Document,
    title: str
):
    """
    Add a professional section heading.
    """

    paragraph = document.add_paragraph()

    paragraph.paragraph_format.space_before = Pt(7)
    paragraph.paragraph_format.space_after = Pt(3)

    run = paragraph.add_run(
        title.upper()
    )

    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(10.5)

    # Add bottom border
    p = paragraph._p

    pPr = p.get_or_add_pPr()

    pBdr = OxmlElement(
        "w:pBdr"
    )

    bottom = OxmlElement(
        "w:bottom"
    )

    bottom.set(
        qn("w:val"),
        "single"
    )

    bottom.set(
        qn("w:sz"),
        "6"
    )

    bottom.set(
        qn("w:space"),
        "1"
    )

    bottom.set(
        qn("w:color"),
        "808080"
    )

    pBdr.append(
        bottom
    )

    pPr.append(
        pBdr
    )

    return paragraph


# ============================================================
# HEADER
# ============================================================

def add_resume_header(
    document: Document,
    header_lines: list[str]
):
    """
    Add candidate name and contact information.
    """

    if not header_lines:

        return

    name = header_lines[0]

    paragraph = document.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    paragraph.paragraph_format.space_after = Pt(2)

    run = paragraph.add_run(
        name
    )

    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(18)

    # Remaining header information
    if len(header_lines) > 1:

        contact = " | ".join(
            header_lines[1:]
        )

        paragraph = document.add_paragraph()

        paragraph.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        paragraph.paragraph_format.space_after = Pt(5)

        run = paragraph.add_run(
            contact
        )

        run.font.name = "Arial"
        run.font.size = Pt(9)


# ============================================================
# BULLET HANDLING
# ============================================================

def is_bullet_line(line: str) -> bool:
    """
    Detect common bullet formats.
    """

    return bool(
        line.startswith(
            (
                "- ",
                "* ",
                "• ",
                "▪ ",
                "● "
            )
        )
        or
        bool(
            __import__("re").match(
                r"^\d+[.)]\s+",
                line
            )
        )
    )


def clean_bullet(line: str) -> str:
    """
    Remove an existing bullet marker.
    """

    line = line.strip()

    line = __import__("re").sub(
        r"^(?:[-*•▪●]|\d+[.)])\s+",
        "",
        line
    )

    return line.strip()


# ============================================================
# ADD SECTION CONTENT
# ============================================================

def add_section_content(
    document: Document,
    lines: list[str]
):
    """
    Add section content while keeping the document ATS-friendly.
    """

    for line in lines:

        line = clean_text(line)

        if not line:

            continue

        paragraph = document.add_paragraph()

        paragraph.paragraph_format.space_after = Pt(2)

        if is_bullet_line(line):

            text = clean_bullet(line)

            paragraph.style = (
                document.styles["Normal"]
            )

            paragraph.paragraph_format.left_indent = (
                Inches(0.18)
            )

            paragraph.paragraph_format.first_line_indent = (
                Inches(-0.12)
            )

            run = paragraph.add_run(
                "• " + text
            )

        else:

            run = paragraph.add_run(
                line
            )

        run.font.name = "Arial"
        run.font.size = Pt(9.5)


# ============================================================
# SKILLS SECTION
# ============================================================

def add_skills_section(
    document: Document,
    lines: list[str]
):
    """
    Add skills in a compact ATS-friendly format.
    """

    if not lines:

        return

    add_section_heading(
        document,
        "Skills"
    )

    for line in lines:

        line = clean_text(line)

        if not line:

            continue

        paragraph = document.add_paragraph()

        paragraph.paragraph_format.space_after = Pt(2)

        run = paragraph.add_run(
            line
        )

        run.font.name = "Arial"
        run.font.size = Pt(9.5)


# ============================================================
# GENERATE DOCX
# ============================================================

def generate_resume_docx(
    resume_text: str,
    output_filename: str = "tailored_resume.docx"
) -> dict:
    """
    Generate a professional ATS-friendly DOCX resume.

    The function does not modify or invent resume content.
    It only formats the supplied resume text.
    """

    resume_text = clean_text(
        resume_text
    )

    if not resume_text:

        return {

            "success": False,

            "message":
                "Cannot generate resume because resume text is empty."
        }

    sections = split_resume_sections(
        resume_text
    )

    document = Document()

    configure_document(
        document
    )

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    add_resume_header(
        document,
        sections["header"]
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    if sections["summary"]:

        add_section_heading(
            document,
            "Professional Summary"
        )

        add_section_content(
            document,
            sections["summary"]
        )

    # --------------------------------------------------------
    # SKILLS
    # --------------------------------------------------------

    if sections["skills"]:

        add_skills_section(
            document,
            sections["skills"]
        )

    # --------------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------------

    if sections["experience"]:

        add_section_heading(
            document,
            "Experience"
        )

        add_section_content(
            document,
            sections["experience"]
        )

    # --------------------------------------------------------
    # PROJECTS
    # --------------------------------------------------------

    if sections["projects"]:

        add_section_heading(
            document,
            "Projects"
        )

        add_section_content(
            document,
            sections["projects"]
        )

    # --------------------------------------------------------
    # EDUCATION
    # --------------------------------------------------------

    if sections["education"]:

        add_section_heading(
            document,
            "Education"
        )

        add_section_content(
            document,
            sections["education"]
        )

    # --------------------------------------------------------
    # CERTIFICATIONS
    # --------------------------------------------------------

    if sections["certifications"]:

        add_section_heading(
            document,
            "Certifications"
        )

        add_section_content(
            document,
            sections["certifications"]
        )

    # --------------------------------------------------------
    # ACHIEVEMENTS
    # --------------------------------------------------------

    if sections["achievements"]:

        add_section_heading(
            document,
            "Achievements"
        )

        add_section_content(
            document,
            sections["achievements"]
        )

    # --------------------------------------------------------
    # PUBLICATIONS
    # --------------------------------------------------------

    if sections["publications"]:

        add_section_heading(
            document,
            "Publications"
        )

        add_section_content(
            document,
            sections["publications"]
        )

    # --------------------------------------------------------
    # OTHER CONTENT
    # --------------------------------------------------------

    if sections["other"]:

        add_section_heading(
            document,
            "Additional Information"
        )

        add_section_content(
            document,
            sections["other"]
        )

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    for section in document.sections:

        footer = section.footer

        paragraph = footer.paragraphs[0]

        paragraph.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        run = paragraph.add_run(
            "ATS-friendly resume"
        )

        run.font.name = "Arial"
        run.font.size = Pt(7)

    # --------------------------------------------------------
    # OUTPUT PATH
    # --------------------------------------------------------

    safe_filename = Path(
        output_filename
    ).name

    if not safe_filename.lower().endswith(
        ".docx"
    ):

        safe_filename += ".docx"

    output_path = (
        OPTIMIZED_DIR /
        safe_filename
    )

    document.save(
        str(output_path)
    )

    return {

        "success":
            True,

        "message":
            "Professional resume DOCX generated successfully.",

        "file":
            str(output_path),

        "filename":
            safe_filename,

        "generated_at":
            datetime.utcnow().isoformat(),

        "format":
            "DOCX"
    }


# ============================================================
# TAILORED RESUME GENERATION
# ============================================================

def generate_tailored_resume(
    optimized_resume: str,
    ats_score: int | float,
    target_score: int = 90,
    filename_prefix: str = "tailored_resume"
) -> dict:
    """
    Generate a DOCX only after the optimized resume has been
    evaluated.

    This function does NOT artificially increase the ATS score.

    The supplied ATS score is recorded as metadata for the
    application workflow.
    """

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"{filename_prefix}_{timestamp}.docx"
    )

    result = generate_resume_docx(
        optimized_resume,
        filename
    )

    result[
        "ats_score"
    ] = ats_score

    result[
        "target_score"
    ] = target_score

    result[
        "target_reached"
    ] = (
        float(ats_score)
        >=
        float(target_score)
    )

    return result