import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

api_key = os.getenv("XAI_API_KEY")

if not api_key:
    print("ERROR: XAI_API_KEY was not found.")
    raise SystemExit

print("XAI_API_KEY found successfully.")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.x.ai/v1"
)

response = client.responses.create(
    model="grok-4.5",
    input="Say hello to Aryaman in one short sentence."
)

print("\nGrok response:")
print(response.output_text)