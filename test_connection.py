# test_connection.py
import requests
import json

# Configuration
SERVER_IP = "192.168.1.37"  # Change this to your server IP
SERVER_PORT = 8000
BASE_URL = f"http://{SERVER_IP}:{SERVER_PORT}"

def test_server_status():
    """Test if server is responding"""
    print("🔍 Testing server status...")
    try:
        response = requests.get(f"{BASE_URL}/status", timeout=5)
        print(f"✅ Server Status: {response.status_code}")
        print(f"📋 Response: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        return False

def test_pair_check():
    """Test pair-check endpoint"""
    print("\n🔍 Testing pair-check...")
    
    # Test data - try different passwords
    test_cases = [
        {"ip": "192.168.1.34", "password": "IMC-MOBILE"},
        {"ip": "192.168.1.34", "password": "imc-mobile"},
        {"ip": "192.168.1.34", "password": ""},
    ]
    
    for i, data in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {data}")
        try:
            response = requests.post(f"{BASE_URL}/pair-check", json=data, timeout=5)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
        except Exception as e:
            print(f"❌ Error: {e}")

def test_login():
    """Test login endpoint"""
    print("\n🔍 Testing login...")
    
    # Test different login combinations
    test_logins = [
        {"userid": "1", "password": "111"},
    ]
    
    for login_data in test_logins:
        print(f"\n📝 Testing login: {login_data['userid']}")
        try:
            response = requests.post(f"{BASE_URL}/login", json=login_data, timeout=5)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"✅ Login successful: {response.json()}")
            else:
                print(f"❌ Login failed: {response.json()}")
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    print("🚀 SyncAnywhere Connection Test")
    print("=" * 40)
    print(f"🌐 Testing server: {BASE_URL}")
    print("=" * 40)
    
    # Test server connectivity first
    if not test_server_status():
        print("\n❌ Cannot connect to server. Check:")
        print("   1. Is SyncAnywhere.exe running?")
        print("   2. Is the IP address correct?")
        print("   3. Are you on the same WiFi network?")
        print("   4. Check Windows Firewall settings")
        return
    
    # Test pair-check
    test_pair_check()
    
    # Test login
    test_login()
    
    print("\n" + "=" * 40)
    print("🏁 Test completed!")

if __name__ == "__main__":
    main()