# Friend Suggestion API - Detailed Documentation

## Overview
The Friend Suggestion system uses a **weighted ranking algorithm** to suggest users based on real-time behavior. Random or static ordering is strictly avoided.

## Priority Ranking
1. **Profile Views (Weight: 10.0)** - Highest priority. Multiple views significantly boost rank.
2. **Comments (Weight: 7.0)** - Very high engagement signal.
3. **Likes (Weight: 5.0)** - High affinity signal.
4. **Session Frequency (Weight: 4.0)** - Frequent appearance in same browsing sessions.
5. **Mutual Follows (Weight: 3.0)** - Shared social connections.
6. **Trending (Weight: 1.0)** - Fallback for new/inactive users.

---

## 1. Get Suggested Friends
Returns a ranked list of users the current user might want to follow.

- **URL:** `/api/v1/feed/suggested-friends/`
- **Method:** `GET`
- **Authentication:** Required (Bearer Token)

### Success Response (200 OK)
```json
{
  "success": true,
  "message": "Friend suggestions retrieved successfully.",
  "data": {
    "total_suggestions": 2,
    "suggestions": [
      {
        "user_id": 5,
        "name": "Iva Ryan",
        "bio": "Photography",
        "profile_photo": "https://...",
        "total_score": 15.0,
        "reason": "You viewed their profile multiple times",
        "mutual_followers": 3,
        "is_following": false
      }
    ]
  }
}
```

---

## 2. View User Profile (with Automatic Tracking)
View a user's public profile. **Profile views are automatically tracked** for authenticated users to improve friend suggestions.

- **URL:** `/api/v1/account/profile/{profile_id}/`
- **Method:** `GET`
- **Authentication:** Optional (tracking only occurs for authenticated users)

### Success Response (200 OK)
```json
{
  "status": 200,
  "success": true,
  "data": {
    "id": 5,
    "user": {
      "id": 5,
      "name": "Iva Ryan",
      "phone": "+1234567890"
    },
    "bio": "Photography",
    "profile_photo": "https://...",
    "cover_photo": "https://...",
    "is_creator": true,
    "followers_count": 150,
    "following_count": 89
  }
}
```

### Automatic Behavior
- **Authenticated Users:** Profile view is automatically tracked, view count incremented, and suggestion scores updated
- **Unauthenticated Users:** Profile data returned without tracking
- **Self-Views:** Not tracked (viewing your own profile doesn't affect suggestions)

> **Note:** The standalone `/api/v1/feed/profile-view/{user_id}/` endpoint is **deprecated** as of 2026-01-31. Profile tracking now happens automatically when viewing profiles.

---

## Behavior-Based Mechanics
- **Automatic Tracking:** Profile views are automatically tracked when authenticated users view profiles via `/api/v1/account/profile/{profile_id}/`
- **Real-time Recalculation:** Scores are updated instantly when a user views a profile, likes a post, or comments
- **Auto-Removal:** Suggested users are automatically removed from the list as soon as you follow them
- **Privacy/Blocking:** Blocked users (both ways) and already followed users are strictly excluded
- **Self-View Prevention:** Viewing your own profile does not create tracking records
- **Bonus for Recency:** Profile views within the last 24 hours provide a 1.5x multiplier to the view score

## Implementation Details
- **Scoring Engine:** `apps/feed/suggestion_engine.py`
- **Models:** `ProfileView`, `UserInteractionScore`
- **Signals:** Automated triggers on `Like`, `Comment`, and `Follow` saving.

---

## Flutter Integration Example

### Viewing a Profile (with Automatic Tracking)
```dart
Future<void> viewUserProfile(int profileId) async {
  // Single API call - tracking happens automatically on backend
  final response = await dio.get(
    '/api/v1/account/profile/$profileId/',
    options: Options(
      headers: {
        'Authorization': 'Bearer $authToken',  // Optional: include for tracking
      },
    ),
  );
  
  if (response.statusCode == 200) {
    final profileData = response.data['data'];
    // Display profile to user
    // Tracking is automatic - no additional API call needed!
  }
}
```

### Getting Friend Suggestions
```dart
Future<List<SuggestedUser>> getSuggestedFriends() async {
  final response = await dio.get(
    '/api/v1/feed/suggested-friends/',
    options: Options(
      headers: {
        'Authorization': 'Bearer $authToken',
      },
    ),
  );
  
  if (response.statusCode == 200) {
    final suggestions = response.data['data']['suggestions'] as List;
    return suggestions.map((s) => SuggestedUser.fromJson(s)).toList();
  }
  
  return [];
}
```

> **Migration Note:** If you were previously calling `/api/v1/feed/profile-view/{user_id}/` separately, you can now remove that call. Profile tracking happens automatically when you call `/api/v1/account/profile/{profile_id}/`.
