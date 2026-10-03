from jobs import get_remote_jobs, filter_jobs


# --------------------------------------------------
# GET JOBS
# --------------------------------------------------

jobs = get_remote_jobs(
    search_term="",
    limit=100
)


# --------------------------------------------------
# USER PREFERENCES
# --------------------------------------------------

preferences = {
    "opportunity_type": "full-time",

    "work_mode": "remote",

    "domains": [
        "ECE",
        "CSE",
        "AI/ML",
        "Marketing"
    ],

    "location": "Anywhere",

    "minimum_stipend": 5000,

    "experience_level": "Fresher"
}


# --------------------------------------------------
# FILTER JOBS
# --------------------------------------------------

filtered_jobs = filter_jobs(
    jobs,
    preferences
)


# --------------------------------------------------
# DISPLAY RESULTS
# --------------------------------------------------

print("\n" + "=" * 60)
print("JOB SEARCH RESULTS")
print("=" * 60)

print(f"Jobs retrieved: {len(jobs)}")
print(f"Jobs after filtering: {len(filtered_jobs)}")

print("=" * 60)


if not filtered_jobs:

    print("\nNo jobs matched the current preferences.")

    print("\nCurrent preferences:")
    print("Opportunity:", preferences["opportunity_type"])
    print("Work mode:", preferences["work_mode"])
    print("Domains:", ", ".join(preferences["domains"]))
    print("Location:", preferences["location"])

else:

    for job in filtered_jobs:

        print("\n" + "=" * 60)

        print("TITLE:", job.get("title"))
        print("COMPANY:", job.get("company"))
        print("TYPE:", job.get("job_type"))
        print("CATEGORY:", job.get("category"))
        print("LOCATION:", job.get("location"))
        print("SALARY:", job.get("salary"))
        print("URL:", job.get("url"))
