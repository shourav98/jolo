"""
Verification Script for Friend Suggestion System
Validates dynamic ranking based on user behavior
"""

import requests
import json
import time

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

def login(phone, password):
    url = f"{BASE_URL}/api/v1/account/login/"
    data = {"phone": phone, "password": password}
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            token = response.json()['data']['access']
            user_id = response.json()['data']['user']['id']
            return token, user_id
        else:
            print_error(f"Login failed: {response.json()}")
            return None, None
    except Exception as e:
        print_error(f"Login error: {str(e)}")
        return None, None

def get_suggestions(token):
    url = f"{API_BASE}/suggested-friends/"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()['data']['suggestions']
        else:
            print_error(f"Failed to get suggestions: {response.json()}")
            return []
    except Exception as e:
        print_error(f"Error getting suggestions: {str(e)}")
        return []

def track_profile_view(token, user_id):
    url = f"{API_BASE}/profile-view/{user_id}/"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            print_success(f"Tracked profile view for user {user_id}")
            return True
        else:
            print_error(f"Failed to track profile view: {response.json()}")
            return False
    except Exception as e:
        print_error(f"Error tracking profile view: {str(e)}")
        return False

def like_post(token, post_id):
    url = f"{API_BASE}/feed/{post_id}/like/"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            print_success(f"Liked post {post_id}")
            return True
        else:
            print_error(f"Failed to like post: {response.json()}")
            return False
    except Exception as e:
        print_error(f"Error liking post: {str(e)}")
        return False

def get_user_posts(token, user_id):
    # This assumes there's a search or feed API that can filter by user
    # If not, we might have to just browse the general feed and hope to find one
    url = f"{API_BASE}/feed/"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            posts = response.json()['data']
            # Simple filtering logic if the API doesn't support it directly
            # This is a bit speculative about the post object structure
            return [p for p in posts if p.get('user_id') == user_id or p.get('profile', {}).get('user_id') == user_id]
        return []
    except:
        return []

def run_verification():
    print("=" * 60)
    print("FRIEND SUGGESTION SYSTEM - VERIFICATION")
    print("=" * 60)
    
    phone = input("Enter Phone: ").strip()
    password = input("Enter Password: ").strip()
    
    token, my_user_id = login(phone, password)
    if not token: return
    
    print_info(f"Connected as User ID: {my_user_id}")
    
    # 1. Get initial suggestions
    initial_suggestions = get_suggestions(token)
    print_info(f"Initial suggestions count: {len(initial_suggestions)}")
    if not initial_suggestions:
        print_warning("No initial suggestions found. Possible reasons: new database or everyone is followed.")
        return

    # Pick the last user in suggestions to see them move up
    target_user = initial_suggestions[-1]
    target_user_id = target_user['user_id']
    target_user_name = target_user['name']
    
    print_info(f"Targeting user: {target_user_name} (ID: {target_user_id}) currently at position {len(initial_suggestions)}")
    
    # 2. View their profile 3 times
    print_info("\nSimulating 3 profile views...")
    for i in range(3):
        track_profile_view(token, target_user_id)
        time.sleep(0.5)
    
    # 3. Check ranking change
    suggestions_after_views = get_suggestions(token)
    new_pos = next((i for i, u in enumerate(suggestions_after_views) if u['user_id'] == target_user_id), -1)
    
    if new_pos != -1:
        print_success(f"User {target_user_name} is now at position {new_pos + 1} (Score: {suggestions_after_views[new_pos]['total_score']})")
        print_info(f"Reason: {suggestions_after_views[new_pos]['reason']}")
    else:
        print_error("Target user disappeared from suggestions!")

    # 4. Like one of their posts if possible
    print_info("\nTrying to find and like a post by target user...")
    # This part depends on the availability of posts
    posts = get_user_posts(token, target_user_id)
    if posts:
        target_post_id = posts[0]['id']
        like_post(token, target_post_id)
        
        # Check ranking again
        suggestions_after_like = get_suggestions(token)
        final_pos = next((i for i, u in enumerate(suggestions_after_like) if u['user_id'] == target_user_id), -1)
        if final_pos != -1:
            print_success(f"User {target_user_name} is now at position {final_pos + 1} (Score: {suggestions_after_like[final_pos]['total_score']})")
        else:
            print_error("Target user disappeared after like!")
    else:
        print_warning("Couldn't find any posts by the target user to like.")

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_verification()
