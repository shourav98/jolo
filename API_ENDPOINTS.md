# Post Menu Actions - API Endpoints Summary

## Base URL
`http://127.0.0.1:8000/api/v1/feed`

---

## Post Owner Actions

### 1. Edit Post
- **Endpoint:** `PUT /feed/{post_id}/`
- **Auth:** Required (Owner only)
- **Body:**
  ```json
  {
    "content": "Updated content",
    "comments_enabled": true
  }
  ```

### 2. Delete Post
- **Endpoint:** `DELETE /feed/{post_id}/`
- **Auth:** Required (Owner only)
- **Body:** None

### 3. Toggle Comments
- **Endpoint:** `POST /feed/{post_id}/toggle-comments/`
- **Auth:** Required (Owner only)
- **Body:** None
- **Response:** Returns new `comments_enabled` status

### 4. Copy Link
- **Endpoint:** `GET /feed/{post_id}/copy-link/`
- **Auth:** Not required
- **Body:** None
- **Response:** Returns shareable URL

---

## Viewer/Follower Actions

### 5. Follow/Unfollow User
- **Endpoint:** `POST /follow/{user_profile_id}/`
- **Auth:** Required
- **Body:** None
- **Response:** Returns `following` status (true/false)

### 6. Mute/Unmute Post
- **Endpoint:** `POST /feed/{post_id}/mute/`
- **Auth:** Required
- **Body:** None
- **Response:** Returns `is_muted` status (true/false)

### 7. Report Post
- **Endpoint:** `POST /feed/{post_id}/report/`
- **Auth:** Required
- **Body:**
  ```json
  {
    "reason": "spam",
    "description": "Optional description"
  }
  ```
- **Valid Reasons:**
  - `harassment`
  - `spam`
  - `violence`
  - `adult_content`
  - `false_info`
  - `hate_speech`
  - `other`

### 8. Block/Unblock User
- **Endpoint:** `POST /user/{user_profile_id}/block/`
- **Auth:** Required
- **Body:** None
- **Response:** Returns `is_blocked` status (true/false)
- **Note:** Automatically unfollows when blocking

---

## Additional Endpoints

### Get Feed List
- **Endpoint:** `GET /feed/`
- **Auth:** Optional (shows public posts if not authenticated)
- **Response:** Array of feed posts with `comments_enabled`, `is_muted`, `is_author_blocked` fields

### Get Single Post
- **Endpoint:** `GET /feed/{post_id}/`
- **Auth:** Optional
- **Response:** Single feed post details

### Create Post
- **Endpoint:** `POST /feed/`
- **Auth:** Required
- **Body:**
  ```json
  {
    "content": "Post content",
    "status": "public"
  }
  ```

### Add Comment
- **Endpoint:** `POST /feed/{post_id}/comments/`
- **Auth:** Required
- **Body:**
  ```json
  {
    "content": "Comment text"
  }
  ```
- **Note:** Returns 403 if comments are disabled

### Get Comments
- **Endpoint:** `GET /feed/{post_id}/comments/`
- **Auth:** Optional
- **Response:** Array of comments

---

## Response Format

All endpoints return responses in this format:

```json
{
  "success": true,
  "status_code": 200,
  "message": "Operation successful",
  "data": {
    // Response data here
  }
}
```

### Error Response
```json
{
  "success": false,
  "status_code": 400,
  "message": "Error description",
  "data": []
}
```

---

## Authentication

Include JWT token in header for authenticated endpoints:

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Get token from login endpoint:
```bash
POST /api/v1/account/login/
{
  "phone": "your_phone",
  "password": "your_password"
}
```

---

## Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found

---

## Testing Tools

1. **Automated Script:** `python test_post_menu.py`
2. **cURL:** See `TESTING_GUIDE.md`
3. **Postman:** Import collection from `api_testing_guide.md`
4. **Django Admin:** `http://127.0.0.1:8000/admin/`

---

## Database Models

### Feed
- Added field: `comments_enabled` (BooleanField, default=True)

### BlockedUser
- `blocker` (ForeignKey to UserProfile)
- `blocked` (ForeignKey to UserProfile)
- `created_at`

### MutedPost
- `user` (ForeignKey to UserProfile)
- `post` (ForeignKey to Feed)
- `created_at`

### ReportedPost
- `reporter` (ForeignKey to UserProfile)
- `post` (ForeignKey to Feed)
- `reason` (CharField with choices)
- `description` (TextField, optional)
- `status` (CharField: pending/reviewed/resolved)
- `created_at`
- `reviewed_at`

---

## Admin Actions

In Django Admin → Feed → Reported posts:
- **Mark as reviewed** - Bulk action
- **Mark as resolved** - Bulk action

---

## Quick Test Commands

```bash
# Login
curl -X POST http://127.0.0.1:8000/api/v1/account/login/ -H "Content-Type: application/json" -d '{"phone":"PHONE","password":"PASS"}'

# Toggle comments
curl -X POST http://127.0.0.1:8000/api/v1/feed/feed/1/toggle-comments/ -H "Authorization: Bearer TOKEN"

# Mute post
curl -X POST http://127.0.0.1:8000/api/v1/feed/feed/1/mute/ -H "Authorization: Bearer TOKEN"

# Report post
curl -X POST http://127.0.0.1:8000/api/v1/feed/feed/1/report/ -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d '{"reason":"spam","description":"Test"}'

# Block user
curl -X POST http://127.0.0.1:8000/api/v1/feed/user/2/block/ -H "Authorization: Bearer TOKEN"
```
