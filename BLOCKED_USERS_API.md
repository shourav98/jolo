# Blocked Users List API - Testing Guide

## Endpoint
**GET** `/api/v1/feed/blocked-users/`

## Description
Retrieves a list of all users blocked by the currently authenticated user, matching the "Blocked Users" page UI.

## Authentication
**Required:** Yes (Bearer Token)

## Request

### Headers
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Method
```
GET
```

### URL
```
http://127.0.0.1:8000/api/v1/feed/blocked-users/
```

## Response

### Success Response (200 OK)

```json
{
  "success": true,
  "status_code": 200,
  "message": "Blocked users retrieved successfully.",
  "data": {
    "total_blocked": 6,
    "blocked_users": [
      {
        "id": 1,
        "blocked_user_id": 5,
        "blocked_user_name": "Iva Ryan",
        "blocked_user_photo": "https://res.cloudinary.com/your-cloud/image/upload/v1234567890/profiles/user5.jpg",
        "blocked_user_bio": "Photography",
        "created_at": "2026-01-23T10:30:00Z"
      },
      {
        "id": 2,
        "blocked_user_id": 8,
        "blocked_user_name": "Frances Swann",
        "blocked_user_photo": "https://res.cloudinary.com/your-cloud/image/upload/v1234567890/profiles/user8.jpg",
        "blocked_user_bio": "Art",
        "created_at": "2026-01-23T09:15:00Z"
      },
      {
        "id": 3,
        "blocked_user_id": 12,
        "blocked_user_name": "James Hall",
        "blocked_user_photo": "https://res.cloudinary.com/your-cloud/image/upload/v1234567890/profiles/user12.jpg",
        "blocked_user_bio": "Musician",
        "created_at": "2026-01-22T18:45:00Z"
      },
      {
        "id": 4,
        "blocked_user_id": 15,
        "blocked_user_name": "Dennis Callis",
        "blocked_user_photo": "https://res.cloudinary.com/your-cloud/image/upload/v1234567890/profiles/user15.jpg",
        "blocked_user_bio": "Design",
        "created_at": "2026-01-22T14:20:00Z"
      },
      {
        "id": 5,
        "blocked_user_id": 18,
        "blocked_user_name": "Stephanie Nicol",
        "blocked_user_photo": "https://res.cloudinary.com/your-cloud/image/upload/v1234567890/profiles/user18.jpg",
        "blocked_user_bio": "Writing",
        "created_at": "2026-01-21T11:00:00Z"
      },
      {
        "id": 6,
        "blocked_user_id": 20,
        "blocked_user_name": "Dennis Callis",
        "blocked_user_photo": "https://res.cloudinary.com/your-cloud/image/upload/v1234567890/profiles/user20.jpg",
        "blocked_user_bio": "Design",
        "created_at": "2026-01-20T16:30:00Z"
      }
    ]
  }
}
```

### Empty List Response (200 OK)

```json
{
  "success": true,
  "status_code": 200,
  "message": "Blocked users retrieved successfully.",
  "data": {
    "total_blocked": 0,
    "blocked_users": []
  }
}
```

### Error Response (401 Unauthorized)

```json
{
  "success": false,
  "status_code": 401,
  "message": "Authentication credentials were not provided.",
  "data": []
}
```

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Blocked relationship ID |
| `blocked_user_id` | Integer | ID of the blocked user |
| `blocked_user_name` | String | Name of the blocked user |
| `blocked_user_photo` | String (URL) | Profile photo URL (Cloudinary) |
| `blocked_user_bio` | String | User's bio/profession |
| `created_at` | DateTime | When the user was blocked |

## Testing in Postman

### 1. Setup Request

**Create a new request:**
- **Name:** Get Blocked Users
- **Method:** GET
- **URL:** `{{base_url}}/api/v1/feed/blocked-users/`
- **Headers:**
  - `Authorization`: `Bearer {{access_token}}`

### 2. Send Request

Click **Send** to retrieve the list of blocked users.

### 3. Expected Behavior

- Returns all users you have blocked
- Ordered by most recently blocked first
- Includes profile photo and bio for each user
- Shows total count of blocked users

## Testing with cURL

```bash
# Get blocked users list
curl -X GET http://127.0.0.1:8000/api/v1/feed/blocked-users/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Use Cases

1. **Display Blocked Users Page**
   - Show list of blocked users in settings
   - Allow users to review who they've blocked
   - Provide unblock option for each user

2. **Blocked Users Count**
   - Display total number of blocked users
   - Show in settings badge/counter

3. **Profile Information**
   - Display user photos in list
   - Show user names and bios
   - Help users identify blocked accounts

## Integration with UI

Based on the provided UI mockup, this endpoint provides all necessary data:

- **Profile Photo** → `blocked_user_photo`
- **User Name** → `blocked_user_name`
- **Bio/Profession** → `blocked_user_bio`
- **Unblock Button** → Use `blocked_user_id` with the block toggle endpoint

## Related Endpoints

- **Block User:** `POST /api/v1/feed/user/{user_id}/block/`
- **Unblock User:** `POST /api/v1/feed/user/{user_id}/block/` (same endpoint, toggles)

## Notes

- Results are ordered by `created_at` descending (most recent first)
- Profile photos are served via Cloudinary CDN
- If user has no profile photo, `blocked_user_photo` will be `null`
- If user has no bio, `blocked_user_bio` will be `null` or empty string
- Requires authentication - only shows users blocked by the current user
