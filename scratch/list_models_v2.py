import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

print("Listing models with google-genai SDK:")
try:
    for m in client.models.list():
        print(f" - {m.name:45s} | display_name: {getattr(m, 'display_name', '')}")
except Exception as e:
    print("Error:", e)
