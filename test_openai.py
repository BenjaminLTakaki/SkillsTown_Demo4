# test_openai.py - Place this in your project directory
import os
import requests
import json

def test_openai_embedding():
    api_key = os.environ.get('OPENAI_API_KEY')
    
    print(f"API Key present: {'Yes' if api_key else 'No'}")
    if api_key:
        print(f"API Key starts with: {api_key[:10]}...")
    
    if not api_key:
        print("❌ OPENAI_API_KEY not set!")
        return False
    
    # Test the embedding API
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "text-embedding-3-small",
        "input": "This is a test sentence"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if 'data' in result and len(result['data']) > 0:
                print("✅ OpenAI API is working correctly!")
                print(f"Embedding dimension: {len(result['data'][0]['embedding'])}")
                return True
            else:
                print("❌ No embedding data returned")
                print(f"Response: {result}")
                return False
        else:
            print(f"❌ API Error {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing OpenAI API Connection...")
    test_openai_embedding()