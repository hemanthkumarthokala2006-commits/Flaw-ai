#!/usr/bin/env python3
"""
Comprehensive Gemini Models Information Viewer
Lists all available Gemini models and their capabilities
"""

import google.generativeai as genai
import os
from dotenv import load_dotenv
from typing import List, Dict
import json

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY not found in .env file")
    exit(1)

genai.configure(api_key=api_key)

# Models used in Flaw AI project
REQUIRED_MODELS = {
    "gemini-2.0-flash": "Main chat model - Fast and efficient",
    "gemini-1.5-pro": "Advanced reasoning and complex tasks",
    "gemini-1.5-flash": "Quick responses and lightweight tasks",
}

def get_supported_generation_methods(model) -> List[str]:
    """Extract supported generation methods from model."""
    methods = []
    if hasattr(model, 'supported_generation_methods'):
        methods = list(model.supported_generation_methods)
    return methods

def get_model_capabilities(model) -> Dict:
    """Extract model capabilities and specifications."""
    capabilities = {
        "name": model.name,
        "display_name": getattr(model, 'display_name', 'N/A'),
        "description": getattr(model, 'description', 'N/A'),
        "supported_generation_methods": get_supported_generation_methods(model),
        "input_token_limit": getattr(model, 'input_token_limit', 'N/A'),
        "output_token_limit": getattr(model, 'output_token_limit', 'N/A'),
    }
    return capabilities

def print_section(title: str, char: str = "="):
    """Print a formatted section header."""
    print(f"\n{char * 60}")
    print(f"  {title}")
    print(f"{char * 60}\n")

def main():
    """Main function to display all Gemini models."""
    
    print_section("🤖 GEMINI MODELS INFORMATION", "=")
    print("Fetching available Gemini models from API...\n")
    
    try:
        # Get all available models
        all_models = list(genai.list_models())
        
        # Filter models that support content generation
        generation_models = [m for m in all_models if 'generateContent' in get_supported_generation_methods(m)]
        
        # Display required models
        print_section("📋 REQUIRED MODELS FOR FLAW AI", "-")
        print(f"Total models in project configuration: {len(REQUIRED_MODELS)}\n")
        
        for model_name, description in REQUIRED_MODELS.items():
            # Try to find the model in available models
            found = next((m for m in generation_models if model_name in m.name), None)
            status = "✅ AVAILABLE" if found else "❌ NOT AVAILABLE"
            print(f"{status} | {model_name}")
            print(f"         └─ {description}\n")
        
        # Display all available models
        print_section("📚 ALL AVAILABLE GENERATION MODELS", "-")
        print(f"Total available models: {len(generation_models)}\n")
        
        for idx, model in enumerate(generation_models, 1):
            capabilities = get_model_capabilities(model)
            
            # Extract model ID (short version)
            model_id = model.name.split('/')[-1] if '/' in model.name else model.name
            
            print(f"{idx}. {model_id}")
            print(f"   Display Name:          {capabilities['display_name']}")
            print(f"   Description:           {capabilities['description'][:80]}...")
            print(f"   Input Token Limit:     {capabilities['input_token_limit']:,}" if capabilities['input_token_limit'] != 'N/A' else f"   Input Token Limit:     {capabilities['input_token_limit']}")
            print(f"   Output Token Limit:    {capabilities['output_token_limit']:,}" if capabilities['output_token_limit'] != 'N/A' else f"   Output Token Limit:    {capabilities['output_token_limit']}")
            print(f"   Capabilities:          {', '.join(capabilities['supported_generation_methods'])}")
            print()
        
        # Model recommendations
        print_section("💡 RECOMMENDATIONS", "-")
        print("For Chat Applications:")
        print("  • Use gemini-2.0-flash for fastest responses")
        print("  • Use gemini-1.5-pro for complex reasoning\n")
        
        print("For Real-time Streaming:")
        print("  • gemini-2.0-flash is recommended (fastest)\n")
        
        print("For Long Context:")
        print("  • gemini-1.5-pro has extended context window\n")
        
        print("For Cost Optimization:")
        print("  • gemini-2.0-flash is most cost-effective\n")
        
        # Display summary
        print_section("📊 SUMMARY", "-")
        print(f"✓ API Connection:        SUCCESSFUL")
        print(f"✓ Total Models:          {len(all_models)}")
        print(f"✓ Generation Models:     {len(generation_models)}")
        print(f"✓ Required Models Found: {sum(1 for m in REQUIRED_MODELS if any(r in m for r in [n for n in REQUIRED_MODELS.keys()]))}")
        print()
        
    except Exception as e:
        print(f"❌ Error fetching models: {e}")
        print("\nMake sure your GEMINI_API_KEY is valid in the .env file")
        exit(1)

if __name__ == "__main__":
    main()
