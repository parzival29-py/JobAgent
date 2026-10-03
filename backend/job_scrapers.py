
import hashlib
import json
import logging
import os
import time
from html import unescape
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)

BRIGHTDATA_API = "https://api.brightdata.com"
SCRAPERAPI_URL = "https://api.scraperapi.com"


def split_urls(value):
    return [
        item.strip()
        for item in (value or "").split(",")
        if item.strip()
    ]


def clean_text(value):
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(
            clean_text(item)
            for item in value
            if item is not None
        )

    if isinstance(value, dict):
        return clean_text(
            value.get("name")
            or value.get("value")
            or value.get("text")
            or value.get("address")
            or ""
        )

    text = BeautifulSoup(
        str(value),
        "html.parser"
    ).get_text(" ", strip=True)

    return unescape(text).strip()


def first_value(record, *keys):
    for key in keys:
        value = record.get(key)

        if value is not None and value != "":
            return value

    return ""


def extract_location(record):
    location = first_value(
        record,
        "location",
        "job_location",
        "candidate_required_location",
        "jobLocation",
        "locations"
    )

    if not location:
        if str(record.get("jobLocationType", "")).upper() == "TELECOMMUTE":
            return "Remote"

        return ""

    if isinstance(location, list):
        return "; ".join(
            filter(None, [extract_location({"location": item}) for item in location])
        )

    if isinstance(location, dict):
        address = location.get("address", location)

        if isinstance(address, dict):
            parts = [
                address.get("addressLocality"),
                address.get("addressRegion"),
                address.get("addressCountry"),
            ]

            result = ", ".join(
                str(part)
                for part in parts
                if part
            )

            return result or clean_text(location.get("name", ""))

        return clean_text(address)

    return clean_text(location)


def normalize_job(record, source):
    if not isinstance(record, dict):
        return None

    title = clean_text(first_value(
        record,
        "title",
        "job_title",
        "position",
        "jobTitle",
        "name"
    ))

    url = clean_text(first_value(
        record,
        "url",
        "job_url",
        "job_link",
        "job_posting_url",
        "link",
        "apply_url"
    ))

    if not title or not url:
        return None

    company = clean_text(first_value(
        record,
        "company",
        "company_name",
        "employer",
        "organization",
        "hiringOrganization"
    ))

    if isinstance(record.get("hiringOrganization"), dict):
        company = clean_text(
            record["hiringOrganization"].get("name", company)
        )

    description = clean_text(first_value(
        record,
        "description",
        "job_description",
        "jobDescription",
        "content"
    ))

    salary = first_value(
        record,
        "salary",
        "salary_range",
        "salary_text",
        "baseSalary",
        "compensation"
    )

    if isinstance(salary, dict):
        salary = clean_text(salary)

    job_type = clean_text(first_value(
        record,
        "job_type",
        "employment_type",
        "employmentType",
        "type"
    ))

    category = clean_text(first_value(
        record,
        "category",
        "job_category",
        "job_function"
    ))

    published = clean_text(first_value(
        record,
        "publication_date",
        "date_posted",
        "datePosted",
        "posted_at"
    ))

    job_id = clean_text(first_value(
        record,
        "id",
        "job_id",
        "job_posting_id"
    ))

    if not job_id:
        job_id = hashlib.sha256(
            url.encode("utf-8")
        ).hexdigest()[:16]

    return {
        "id": job_id,
        "title": title,
        "company": company,
        "url": url,
        "category": category,
        "job_type": job_type,
        "location": extract_location(record),
        "salary": clean_text(salary),
        "publication_date": published,
        "description": description,
        "source": source
    }


def extract_job_postings(value):
    found = []

    if isinstance(value, list):
        for item in value:
            found.extend(extract_job_postings(item))

    elif isinstance(value, dict):
        types = value.get("@type", [])
        if isinstance(types, str):
            types = [types]

        if any(
            str(item).lower() == "jobposting"
            for item in types
        ):
            found.append(value)

        graph = value.get("@graph")

        if graph:
            found.extend(extract_job_postings(graph))

    return found


def parse_jobposting_jsonld(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"}
    ):
        if not script.string and not script.get_text(strip=True):
            continue

        raw_json = script.string or script.get_text(strip=True)

        try:
            data = json.loads(raw_json)
        except (json.JSONDecodeError, TypeError):
            continue

        for record in extract_job_postings(data):
            record = dict(record)
            record.setdefault("url", page_url)

            normalized = normalize_job(
                record,
                "ScraperAPI"
            )

            if normalized:
                jobs.append(normalized)

    return jobs


def get_scraperapi_jobs():
    api_key = os.getenv("SCRAPERAPI_KEY")
    target_urls = split_urls(
        os.getenv("SCRAPERAPI_TARGET_URLS")
    )

    if not api_key or not target_urls:
        return []

    render = (
        os.getenv("SCRAPERAPI_RENDER", "false").lower()
        == "true"
    )

    jobs = []

    for target_url in target_urls:
        try:
            response = requests.get(
                SCRAPERAPI_URL,
                params={
                    "api_key": api_key,
                    "url": target_url,
                    "render": str(render).lower()
                },
                timeout=120
            )

            response.raise_for_status()

            jobs.extend(
                parse_jobposting_jsonld(
                    response.text,
                    target_url
                )
            )

        except requests.RequestException as error:
            logger.warning(
                "ScraperAPI failed for %s: %s",
                target_url,
                error
            )

    return jobs


def get_brightdata_records():
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    dataset_id = os.getenv("BRIGHTDATA_DATASET_ID")
    job_urls = split_urls(
        os.getenv("BRIGHTDATA_JOB_URLS")
    )

    if not api_key or not dataset_id or not job_urls:
        return []

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "input": [
            {"url": url}
            for url in job_urls
        ]
    }

    if len(job_urls) <= 20:
        response = requests.post(
            f"{BRIGHTDATA_API}/datasets/v3/scrape",
            params={
                "dataset_id": dataset_id,
                "format": "json"
            },
            headers=headers,
            json=payload,
            timeout=90
        )

        if response.status_code != 202:
            response.raise_for_status()
            return response.json()

        snapshot_id = response.json().get("snapshot_id")

        if not snapshot_id:
            raise RuntimeError(
                "Bright Data returned no snapshot ID."
            )

    else:
        response = requests.post(
            f"{BRIGHTDATA_API}/datasets/v3/trigger",
            params={
                "dataset_id": dataset_id,
                "format": "json"
            },
            headers=headers,
            json=payload,
            timeout=90
        )

        response.raise_for_status()

        snapshot_id = response.json().get("snapshot_id")

        if not snapshot_id:
            raise RuntimeError(
                "Bright Data returned no snapshot ID."
            )

    deadline = time.monotonic() + 300

    while time.monotonic() < deadline:
        progress_response = requests.get(
            f"{BRIGHTDATA_API}/datasets/v3/progress/{snapshot_id}",
            headers=headers,
            timeout=30
        )

        progress_response.raise_for_status()

        status = progress_response.json().get("status")

        if status == "ready":
            results_response = requests.get(
                f"{BRIGHTDATA_API}/datasets/v3/snapshot/{snapshot_id}",
                params={"format": "json"},
                headers=headers,
                timeout=90
            )

            results_response.raise_for_status()
            return results_response.json()

        if status == "failed":
            raise RuntimeError(
                "Bright Data scraping job failed."
            )

        time.sleep(5)

    raise TimeoutError(
        "Bright Data scraping timed out. Check the dashboard for status."
    )


def get_brightdata_jobs():
    try:
        records = get_brightdata_records()
    except (requests.RequestException, RuntimeError, TimeoutError) as error:
        logger.warning("Bright Data failed: %s", error)
        return []

    if isinstance(records, dict):
        for key in ("data", "results", "items", "jobs"):
            if isinstance(records.get(key), list):
                records = records[key]
                break
        else:
            records = [records]

    if not isinstance(records, list):
        return []

    jobs = []

    for record in records:
        normalized = normalize_job(
            record,
            "Bright Data"
        )

        if normalized:
            jobs.append(normalized)

    return jobs


def get_scraped_jobs():
    jobs = []

    jobs.extend(get_brightdata_jobs())
    jobs.extend(get_scraperapi_jobs())

    unique_jobs = []
    seen_urls = set()

    for job in jobs:
        url = job.get("url", "").strip().rstrip("/").lower()

        if not url or url in seen_urls:
            continue

        seen_urls.add(url)
        unique_jobs.append(job)

    return unique_jobs
