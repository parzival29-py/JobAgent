from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

response = client.responses.create(
    model="gpt-5.6",
    input="Say hello to Aryaman and confirm that the Job Application Agent is connected to OpenAI."
)

print(response.output_text)