"""
Quick setup script to test AI mapping with Gemini.
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

# Load environment variables
load_dotenv()

print("🤖 AI Mapping Setup Check")
print("=" * 50)

# Check if API key is set
api_key = os.getenv('GEMINI_API_KEY')
if not api_key or api_key == 'your_gemini_api_key_here':
    print("❌ GEMINI_API_KEY not found in .env file")
    print("\n📝 Setup steps:")
    print("1. Get free API key: https://makersuite.google.com/app/apikey")
    print("2. Add to .env file: GEMINI_API_KEY=your_key_here")
    print("3. Set AI_PROVIDER=gemini in .env")
    sys.exit(1)

print(f"✅ API key found: {api_key[:10]}...")

# Check if package is installed
try:
    import google.generativeai as genai
    print("✅ google-generativeai package installed")
except ImportError:
    print("❌ google-generativeai package not installed")
    print("   Install with: pip install google-generativeai")
    sys.exit(1)

# Test API connection
try:
    genai.configure(api_key=api_key)
    # Try gemini-2.5-flash first (recommended free model)
    model_name = os.getenv('AI_MODEL', 'gemini-2.5-flash')
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'Hello' if you can read this.")
        print(f"✅ API connection successful")
        print(f"   Model: {model_name}")
        print(f"   Response: {response.text.strip()}")
    except Exception as e1:
        # Try alternative model names
        alt_models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest', 'gemini-pro-latest']
        for alt_model in alt_models:
            try:
                model = genai.GenerativeModel(alt_model)
                response = model.generate_content("Say 'Hello' if you can read this.")
                print(f"✅ API connection successful")
                print(f"   Model: {alt_model}")
                print(f"   Response: {response.text.strip()}")
                print(f"\n💡 Update your .env: AI_MODEL={alt_model}")
                break
            except:
                continue
        else:
            raise e1
except Exception as e:
    print(f"❌ API connection failed: {e}")
    print("   Check your API key is correct")
    print("   Run: python list_gemini_models.py to see available models")
    sys.exit(1)

print("\n" + "=" * 50)
print("✅ All checks passed! AI mapping is ready to use.")
print("\n💡 Next steps:")
print("   python main.py interactive samples/amazon_invoice.png")
