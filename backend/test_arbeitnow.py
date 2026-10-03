from jobs import get_arbeitnow_jobs


print("=" * 60)
print("ARBEITNOW JOB TEST")
print("=" * 60)

jobs = get_arbeitnow_jobs(limit=10)

print(f"Jobs retrieved: {len(jobs)}")

for job in jobs:

    print("=" * 60)

    print("TITLE:", job["title"])
    print("COMPANY:", job["company"])
    print("TYPE:", job["job_type"])
    print("LOCATION:", job["location"])
    print("URL:", job["url"])