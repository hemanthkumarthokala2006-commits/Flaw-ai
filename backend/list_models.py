#!/usr/bin/env python3
"""
Simple Gemini Models Lister
Shows all available Gemini models that can be used in Flaw AI
"""

import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERROR: GEMINI_API_KEY not found in .env file")
    exit(1)

genai.configure(api_key=api_key)

# Currently used in Flaw AI
CURRENT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

print("\n" + "="*70)
print("AVAILABLE GEMINI MODELS FOR FLAW AI PROJECT")
print("="*70 + "\n")

try:
    models = genai.list_models()
    
    # Filter for generateContent capability
    generation_models = []
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            model_id = m.name.split('/')[-1] if '/' in m.name else m.name
            generation_models.append({
                'id': model_id,
                'name': m.name,
                'input_tokens': getattr(m, 'input_token_limit', 'N/A'),
                'output_tokens': getattr(m, 'output_token_limit', 'N/A'),
                'description': getattr(m, 'description', 'N/A')[:80]
            })
    
    # Display models
    print(f"CURRENT MODEL (in .env): {CURRENT_MODEL}\n")
    print("-" * 70)
    print(f"{'MODEL NAME':<30} {'INPUT TOKENS':<20} {'OUTPUT TOKENS':<20}")
    print("-" * 70)
    
    for model in generation_models:
        marker = "[CURRENT]" if model['id'] == CURRENT_MODEL else ""
        print(f"{model['id']:<30} {str(model['input_tokens']):<20} {str(model['output_tokens']):<20} {marker}")
    
    print("-" * 70)
    print(f"\nTotal available models: {len(generation_models)}\n")
    
    # Recommendations
    print("RECOMMENDED MODELS FOR THIS PROJECT:")
    print("-" * 70)
    print("1. gemini-2.0-flash         - FASTEST, recommended for real-time chat")
    print("2. gemini-2.5-flash         - Latest flash model, good balance")
    print("3. gemini-1.5-pro           - Best for complex reasoning")
    print("4. gemini-1.5-flash         - Lightweight alternative")
    print("\n")
    
    # How to use
    print("HOW TO USE A DIFFERENT MODEL:")
    print("-" * 70)
    print("Edit backend/.env file and change:")
    print("GEMINI_MODEL=gemini-2.0-flash")
    print("\nOr set it in your code:")
    print("genai.configure(model='gemini-2.0-flash')")
    print("\n" + "="*70 + "\n")
    
except Exception as e:
    print(f"ERROR: {e}")
    print("\nTroubleshoot:")
    print("1. Check GEMINI_API_KEY in .env file")
    print("2. Verify API key is valid")
    print("3. Check internet connection")
    exit(1)
