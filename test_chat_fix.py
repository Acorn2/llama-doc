#!/usr/bin/env python3
"""
Test script to verify the chat endpoint fix
"""

import requests
import json
from datetime import datetime

def test_chat_endpoint():
    """Test the chat endpoint to verify the schema fix"""
    
    # Test data
    test_data = {
        "kb_id": "test-kb-id",
        "message": "Hello, this is a test message",
        "conversation_id": None,
        "use_agent": False
    }
    
    # API endpoint
    url = "http://localhost:8000/api/v1/conversations/chat"
    
    try:
        print("🧪 Testing chat endpoint...")
        print(f"📤 Request data: {json.dumps(test_data, indent=2)}")
        
        response = requests.post(url, json=test_data, timeout=30)
        
        print(f"📊 Status code: {response.status_code}")
        print(f"📥 Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"✅ Success! Response data: {json.dumps(response_data, indent=2, default=str)}")
            
            # Validate response structure
            required_fields = ["conversation_id", "message", "sources", "processing_time"]
            for field in required_fields:
                if field not in response_data:
                    print(f"❌ Missing field: {field}")
                    return False
                    
            print("✅ All required fields present in response")
            return True
            
        else:
            print(f"❌ Error response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the server is running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting chat endpoint test...")
    success = test_chat_endpoint()
    
    if success:
        print("🎉 Test completed successfully!")
    else:
        print("💥 Test failed!")