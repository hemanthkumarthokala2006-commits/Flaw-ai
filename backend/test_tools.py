import google.generativeai as genai
from google.generativeai.types import content_types

try:
    tool = genai.protos.Tool(google_search=genai.protos.GoogleSearch())
    print("tool created")
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        tools=[tool]
    )
    print("model created with tool")
except Exception as e:
    print("Error:", e)
