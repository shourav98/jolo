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

## 2. Track Profile View
Informs the system that a profile has been viewed, updating the ranking score.

- **URL:** `/api/v1/feed/profile-view/{user_id}/`
- **Method:** `POST`
- **Authentication:** Required (Bearer Token)

### Request Body (Optional)
```json
{
  "session_id": "optional-uuid-string"
}
```

### Success Response (200 OK)
```json
{
  "success": true,
  "message": "Profile view tracked successfully.",
  "data": {
    "view_count": 5,
    "viewed_user": "Iva Ryan"
  }
}
```

---

## Behavior-Based Mechanics
- **Real-time Recalculation:** Scores are updated instantly when a user views a profile, likes a post, or comments.
- **Auto-Removal:** Suggested users are automatically removed from the list as soon as you follow them.
- **Privacy/Blocking:** Blocked users (both ways) and already followed users are strictly excluded.
- **Bonus for Recency:** Profile views within the last 24 hours provide a 1.5x multiplier to the view score.

## Implementation Details
- **Scoring Engine:** `apps/feed/suggestion_engine.py`
- **Models:** `ProfileView`, `UserInteractionScore`
- **Signals:** Automated triggers on `Like`, `Comment`, and `Follow` saving.
