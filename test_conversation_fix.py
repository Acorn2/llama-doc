#!/usr/bin/env python3

import requests
import json
import time

# Test the conversation creation endpoint
BASE_URL = 'http://localhost:8000'

def test_conversation_creation():
    """Test conversation creation with proper user authentication"""
    
    # First register and login
    register_data = {
        'email': f'test_conv_{int(time.time())}@example.com',
        'password': 'password123',
        'username': 'testconv'
    }

    try:
        # Register
        print("=== Testing Conversation Creation Fix ===")
        response = requests.post(f'{BASE_URL}/api/v1/users/register', json=register_data)
        if response.status_code in [200, 201]:
            print('✅ User registered successfully')
        else:
            print(f'❌ Registration failed: Status {response.status_code}, Response: {response.text}')
            return False
        
        # Login
        login_data = {
            'login_credential': register_data['email'],
            'password': register_data['password']
        }
        
        response = requests.post(f'{BASE_URL}/api/v1/users/login', json=login_data)
        if response.status_code == 200:
            data = response.json()
            token = data['access_token']
            print('✅ User logged in successfully')
        else:
            print(f'❌ Login failed: {response.text}')
            return False
        
        # Create knowledge base
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        kb_data = {
            'name': 'Test KB for Conversation',
            'description': 'Test knowledge base',
            'is_public': False
        }
        
        response = requests.post(f'{BASE_URL}/api/v1/knowledge-bases/', json=kb_data, headers=headers)
        if response.status_code in [200, 201]:
            kb_response = response.json()
            kb_id = kb_response['id']
            print(f'✅ Knowledge base created: {kb_id}')
        else:
            print(f'❌ KB creation failed: Status {response.status_code}, Response: {response.text}')
            return False
        
        # Create conversation
        conv_data = {
            'kb_id': kb_id,
            'title': 'Test Conversation'
        }
        
        response = requests.post(f'{BASE_URL}/api/v1/conversations/', json=conv_data, headers=headers)
        if response.status_code == 200:
            conv_response = response.json()
            print(f'✅ Conversation created successfully!')
            print(f'   Conversation ID: {conv_response["conversation"]["id"]}')
            print(f'   Title: {conv_response["conversation"]["title"]}')
            print(f'   KB ID: {conv_response["conversation"]["kb_id"]}')
            return True
        else:
            print(f'❌ Conversation creation failed: {response.text}')
            return False
            
    except Exception as e:
        print(f'❌ Test failed with exception: {e}')
        return False

if __name__ == "__main__":
    success = test_conversation_creation()
    if success:
        print("\n🎉 All tests passed! The conversation creation fix is working.")
    else:
        print("\n💥 Tests failed. Please check the server logs.")