"""
Test Script for Post Menu Actions
Run this script to test all implemented endpoints
"""

import requests
import json

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1/feed"

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

# Step 1: Login
def login(phone, password):
    print_info("Step 1: Logging in...")
    url = f"{BASE_URL}/api/v1/account/login/"
    data = {"phone": phone, "password": password}
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            token = response.json()['data']['access']
            print_success(f"Login successful! Token: {token[:20]}...")
            return token
        else:
            print_error(f"Login failed: {response.json()}")
            return None
    except Exception as e:
        print_error(f"Login error: {str(e)}")
        return None

# Step 2: Create a test post
def create_test_post(token):
    print_info("\nStep 2: Creating a test post...")
    url = f"{API_BASE}/feed/"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"content": "Test post for menu actions - created by test script"}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 201:
            post_id = response.json()['data']['id']
            print_success(f"Post created successfully! Post ID: {post_id}")
            return post_id
        else:
            print_error(f"Post creation failed: {response.json()}")
            return None
    except Exception as e:
        print_error(f"Post creation error: {str(e)}")
        return None

# Step 3: Toggle comments
def test_toggle_comments(token, post_id):
    print_info("\nStep 3: Testing toggle comments...")
    url = f"{API_BASE}/feed/{post_id}/toggle-comments/"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Disable comments
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            data = response.json()['data']
            print_success(f"Comments toggled! Enabled: {data['comments_enabled']}")
            
            # Enable comments again
            response = requests.post(url, headers=headers)
            if response.status_code == 200:
                data = response.json()['data']
                print_success(f"Comments toggled again! Enabled: {data['comments_enabled']}")
                return True
        else:
            print_error(f"Toggle comments failed: {response.json()}")
            return False
    except Exception as e:
        print_error(f"Toggle comments error: {str(e)}")
        return False

# Step 4: Copy link
def test_copy_link(post_id):
    print_info("\nStep 4: Testing copy link...")
    url = f"{API_BASE}/feed/{post_id}/copy-link/"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            link = response.json()['data']['link']
            print_success(f"Link generated: {link}")
            return True
        else:
            print_error(f"Copy link failed: {response.json()}")
            return False
    except Exception as e:
        print_error(f"Copy link error: {str(e)}")
        return False

# Step 5: Mute post
def test_mute_post(token, post_id):
    print_info("\nStep 5: Testing mute post...")
    url = f"{API_BASE}/feed/{post_id}/mute/"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Mute
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            data = response.json()['data']
            print_success(f"Post muted! Status: {data['is_muted']}")
            
            # Unmute
            response = requests.post(url, headers=headers)
            if response.status_code == 200:
                data = response.json()['data']
                print_success(f"Post unmuted! Status: {data['is_muted']}")
                return True
        else:
            print_error(f"Mute post failed: {response.json()}")
            return False
    except Exception as e:
        print_error(f"Mute post error: {str(e)}")
        return False

# Step 6: Report post
def test_report_post(token, post_id):
    print_info("\nStep 6: Testing report post...")
    url = f"{API_BASE}/feed/{post_id}/report/"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "reason": "spam",
        "description": "This is a test report from the test script"
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 201:
            report_data = response.json()['data']
            print_success(f"Post reported! Report ID: {report_data['id']}, Reason: {report_data['reason_display']}")
            return True
        elif response.status_code == 400 and "already reported" in response.json()['message']:
            print_warning("Post already reported (expected if running test multiple times)")
            return True
        else:
            print_error(f"Report post failed: {response.json()}")
            return False
    except Exception as e:
        print_error(f"Report post error: {str(e)}")
        return False

# Step 7: Test comment restriction
def test_comment_restriction(token, post_id):
    print_info("\nStep 7: Testing comment restriction...")
    
    # First, disable comments
    toggle_url = f"{API_BASE}/feed/{post_id}/toggle-comments/"
    headers = {"Authorization": f"Bearer {token}"}
    requests.post(toggle_url, headers=headers)
    
    # Try to comment
    comment_url = f"{API_BASE}/feed/{post_id}/comments/"
    data = {"content": "This comment should fail"}
    
    try:
        response = requests.post(comment_url, json=data, headers=headers)
        if response.status_code == 403:
            print_success("Comment correctly blocked when comments are disabled!")
            
            # Re-enable comments
            requests.post(toggle_url, headers=headers)
            return True
        else:
            print_error(f"Comment restriction test failed: {response.json()}")
            return False
    except Exception as e:
        print_error(f"Comment restriction error: {str(e)}")
        return False

# Step 8: Edit post
def test_edit_post(token, post_id):
    print_info("\nStep 8: Testing edit post...")
    url = f"{API_BASE}/feed/{post_id}/"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"content": "Updated content - edited by test script"}
    
    try:
        response = requests.put(url, json=data, headers=headers)
        if response.status_code == 200:
            print_success("Post edited successfully!")
            return True
        else:
            print_error(f"Edit post failed: {response.json()}")
            return False
    except Exception as e:
        print_error(f"Edit post error: {str(e)}")
        return False

# Step 9: Get feed list (verify post appears)
def test_get_feed(token):
    print_info("\nStep 9: Testing get feed list...")
    url = f"{API_BASE}/feed/"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            feeds = response.json()['data']
            print_success(f"Feed list retrieved! Total posts: {len(feeds)}")
            if feeds:
                first_post = feeds[0]
                print_info(f"  First post: ID={first_post['id']}, comments_enabled={first_post['comments_enabled']}")
            return True
        else:
            print_error(f"Get feed failed: {response.json()}")
            return False
    except Exception as e:
        print_error(f"Get feed error: {str(e)}")
        return False

# Main test runner
def run_all_tests():
    print("=" * 60)
    print("POST MENU ACTIONS - AUTOMATED TEST SUITE")
    print("=" * 60)
    
    # Get credentials
    print("\nPlease enter your credentials:")
    phone = input("Phone number: ").strip()
    password = input("Password: ").strip()
    
    # Login
    token = login(phone, password)
    if not token:
        print_error("\nTests aborted - login failed")
        return
    
    # Create test post
    post_id = create_test_post(token)
    if not post_id:
        print_error("\nTests aborted - post creation failed")
        return
    
    # Run all tests
    results = {
        "Toggle Comments": test_toggle_comments(token, post_id),
        "Copy Link": test_copy_link(post_id),
        "Mute Post": test_mute_post(token, post_id),
        "Report Post": test_report_post(token, post_id),
        "Comment Restriction": test_comment_restriction(token, post_id),
        "Edit Post": test_edit_post(token, post_id),
        "Get Feed": test_get_feed(token),
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
    
    print(f"\n{Colors.BLUE}Total: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print_success("\n🎉 All tests passed!")
    else:
        print_warning(f"\n⚠ {total - passed} test(s) failed")
    
    print(f"\n{Colors.YELLOW}Note: Post ID {post_id} was created for testing.{Colors.END}")
    print(f"{Colors.YELLOW}You can delete it manually or keep it for further testing.{Colors.END}")

if __name__ == "__main__":
    run_all_tests()
