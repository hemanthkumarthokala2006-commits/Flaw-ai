import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        model_id = m.name.split('/')[-1]
        print(f"{model_id} | Input: {m.input_token_limit} | Output: {m.output_token_limit}")
