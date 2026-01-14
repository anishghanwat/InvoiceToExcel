"""
List available Gemini models for your API key.
Useful for finding the correct model name if the default doesn't work.
"""
import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("❌ GEMINI_API_KEY not found in .env file")
    sys.exit(1)

try:
    genai.configure(api_key=api_key)
    
    print("🔍 Listing available Gemini models...")
    print("=" * 50)
    
    # List all available models
    models = genai.list_models()
    
    available_models = []
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            model_name = model.name.replace('models/', '')
            available_models.append(model_name)
            print(f"✅ {model_name}")
            if model.display_name:
                print(f"   Display: {model.display_name}")
    
    print("\n" + "=" * 50)
    if available_models:
        print(f"\n💡 Found {len(available_models)} available model(s)")
        print(f"   Recommended: {available_models[0]}")
        print(f"\n   Update your .env file:")
        print(f"   AI_MODEL={available_models[0]}")
    else:
        print("❌ No models found with generateContent support")
        
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
