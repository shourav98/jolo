# Quick Manual Testing Guide

## Prerequisites
Your Django server is already running at `http://127.0.0.1:8000`

---

## 🚀 Option 1: Postman Testing (Recommended)

### Step 1: Setup Postman

1. **Open Postman** (or download from [postman.com](https://www.postman.com/downloads/))
2. **Create a new Collection** named "Post Menu Actions"
3. **Set Collection Variables:**
   - Click on the collection → Variables tab
   - Add these variables:

| Variable | Initial Value | Current Value |
|----------|---------------|---------------|
| `base_url` | `http://127.0.0.1:8000` | `http://127.0.0.1:8000` |
| `access_token` | (leave empty) | (will be filled after login) |
| `post_id` | `1` | `1` |
| `user_id` | `1` | `1` |

### Step 2: Authentication Setup

**Create a new request: "Login"**

- **Method:** POST
- **URL:** `{{base_url}}/api/v1/account/login/`
- **Headers:**
  - `Content-Type`: `application/json`
- **Body (raw JSON):**
```json
{
  "phone": "your_phone_number",
  "password": "your_password"
}
```
- **Tests (Auto-save token):**
```javascript
if (pm.response.code === 200) {
    var jsonData = pm.response.json();
    pm.collectionVariables.set("access_token", jsonData.data.access);
    console.log("Token saved:", jsonData.data.access);
}
```

**Send the request** and the token will be automatically saved!

### Step 3: Create Test Requests

#### A. Toggle Comments

- **Name:** Toggle Comments
- **Method:** POST
- **URL:** `{{base_url}}/api/v1/feed/feed/{{post_id}}/toggle-comments/`
- **Headers:**
  - `Authorization`: `Bearer {{access_token}}`
- **Body:** None

**Expected Response:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Comments disabled successfully.",
  "data": {
    "feed_id": 1,
    "comments_enabled": false
  }
}
```

#### B. Copy Link

- **Name:** Copy Link
- **Method:** GET
- **URL:** `{{base_url}}/api/v1/feed/feed/{{post_id}}/copy-link/`
- **Headers:** None (public endpoint)
- **Body:** None

**Expected Response:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Post link generated successfully.",
  "data": {
    "feed_id": 1,
    "link": "http://127.0.0.1:8000/feed/1/"
  }
}
```

#### C. Mute Post

- **Name:** Mute Post
- **Method:** POST
- **URL:** `{{base_url}}/api/v1/feed/feed/{{post_id}}/mute/`
- **Headers:**
  - `Authorization`: `Bearer {{access_token}}`
- **Body:** None

**Expected Response:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Post muted successfully.",
  "data": {
    "feed_id": 1,
    "is_muted": true
  }
}
```

#### D. Report Post

- **Name:** Report Post
- **Method:** POST
- **URL:** `{{base_url}}/api/v1/feed/feed/{{post_id}}/report/`
- **Headers:**
  - `Authorization`: `Bearer {{access_token}}`
  - `Content-Type`: `application/json`
- **Body (raw JSON):**
```json
{
  "reason": "spam",
  "description": "This post contains spam content"
}
```

**Valid Reasons:**
- `harassment`
- `spam`
- `violence`
- `adult_content`
- `false_info`
- `hate_speech`
- `other`

**Expected Response:**
```json
{
  "success": true,
  "status_code": 201,
  "message": "Post reported successfully. Our team will review it.",
  "data": {
    "id": 1,
    "post_id": 1,
    "reason": "spam",
    "reason_display": "Spam or Misleading",
    "description": "This post contains spam content",
    "status": "pending",
    "created_at": "2026-01-21T14:40:00Z"
  }
}
```

#### E. Block User

- **Name:** Block User
- **Method:** POST
- **URL:** `{{base_url}}/api/v1/feed/user/{{user_id}}/block/`
- **Headers:**
  - `Authorization`: `Bearer {{access_token}}`
- **Body:** None

**Expected Response:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "User blocked successfully.",
  "data": {
    "user_id": 2,
    "user_name": "John Doe",
    "is_blocked": true
  }
}
```

#### F. Unfollow User

- **Name:** Unfollow User
- **Method:** POST
- **URL:** `{{base_url}}/api/v1/feed/follow/{{user_id}}/`
- **Headers:**
  - `Authorization`: `Bearer {{access_token}}`
- **Body:** None

**Expected Response:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Unfollowed successfully.",
  "data": {
    "following": false
  }
}
```

#### G. Edit Post

- **Name:** Edit Post
- **Method:** PUT
- **URL:** `{{base_url}}/api/v1/feed/feed/{{post_id}}/`
- **Headers:**
  - `Authorization`: `Bearer {{access_token}}`
  - `Content-Type`: `application/json`
- **Body (raw JSON):**
```json
{
  "content": "Updated post content from Postman"
}
```

**Expected Response:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Feed updated successfully.",
  "data": {
    "id": 1,
    "content": "Updated post content from Postman",
    "comments_enabled": true,
    ...
  }
}
```

#### H. Delete Post

- **Name:** Delete Post
- **Method:** DELETE
- **URL:** `{{base_url}}/api/v1/feed/feed/{{post_id}}/`
- **Headers:**
  - `Authorization`: `Bearer {{access_token}}`
- **Body:** None

**Expected Response:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Feed deleted successfully.",
  "data": {
    "feed_id": 1
  }
}
```

### Step 4: Testing Workflow in Postman

**Complete Test Sequence:**

1. **Login** → Get token (auto-saved)
2. **Create a Post** (optional, or use existing post ID)
3. **Toggle Comments** → Disable comments
4. **Try to Comment** → Should fail with 403
5. **Toggle Comments** → Re-enable comments
6. **Copy Link** → Get shareable URL
7. **Mute Post** → Mute the post
8. **Mute Post** → Unmute (toggle)
9. **Report Post** → Submit report
10. **Block User** → Block a user
11. **Edit Post** → Update content
12. **Delete Post** → Remove post (last step)

### Step 5: Import Pre-made Collection

**Copy this JSON and import into Postman:**

1. Click **Import** in Postman
2. Select **Raw text**
3. Paste the JSON below
4. Click **Import**

```json
{
  "info": {
    "name": "Post Menu Actions",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://127.0.0.1:8000"
    },
    {
      "key": "access_token",
      "value": ""
    },
    {
      "key": "post_id",
      "value": "1"
    },
    {
      "key": "user_id",
      "value": "2"
    }
  ],
  "item": [
    {
      "name": "1. Login",
      "event": [
        {
          "listen": "test",
          "script": {
            "exec": [
              "if (pm.response.code === 200) {",
              "    var jsonData = pm.response.json();",
              "    pm.collectionVariables.set(\"access_token\", jsonData.data.access);",
              "    console.log(\"Token saved:\", jsonData.data.access);",
              "}"
            ]
          }
        }
      ],
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"phone\": \"your_phone\",\n  \"password\": \"your_password\"\n}"
        },
        "url": {
          "raw": "{{base_url}}/api/v1/account/login/",
          "host": ["{{base_url}}"],
          "path": ["api", "v1", "account", "login", ""]
        }
      }
    },
    {
      "name": "2. Toggle Comments",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{access_token}}"
          }
        ],
        "url": {
          "raw": "{{base_url}}/api/v1/feed/feed/{{post_id}}/toggle-comments/",
          "host": ["{{base_url}}"],
          "path": ["api", "v1", "feed", "feed", "{{post_id}}", "toggle-comments", ""]
        }
      }
    },
    {
      "name": "3. Copy Link",
      "request": {
        "method": "GET",
        "url": {
          "raw": "{{base_url}}/api/v1/feed/feed/{{post_id}}/copy-link/",
          "host": ["{{base_url}}"],
          "path": ["api", "v1", "feed", "feed", "{{post_id}}", "copy-link", ""]
        }
      }
    },
    {
      "name": "4. Mute Post",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{access_token}}"
          }
        ],
        "url": {
          "raw": "{{base_url}}/api/v1/feed/feed/{{post_id}}/mute/",
          "host": ["{{base_url}}"],
          "path": ["api", "v1", "feed", "feed", "{{post_id}}", "mute", ""]
        }
      }
    },
    {
      "name": "5. Report Post",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{access_token}}"
          },
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"reason\": \"spam\",\n  \"description\": \"Test report from Postman\"\n}"
        },
        "url": {
          "raw": "{{base_url}}/api/v1/feed/feed/{{post_id}}/report/",
          "host": ["{{base_url}}"],
          "path": ["api", "v1", "feed", "feed", "{{post_id}}", "report", ""]
        }
      }
    },
    {
      "name": "6. Block User",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{access_token}}"
          }
        ],
        "url": {
          "raw": "{{base_url}}/api/v1/feed/user/{{user_id}}/block/",
          "host": ["{{base_url}}"],
          "path": ["api", "v1", "feed", "user", "{{user_id}}", "block", ""]
        }
      }
    },
    {
      "name": "7. Edit Post",
      "request": {
        "method": "PUT",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{access_token}}"
          },
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"content\": \"Updated from Postman\"\n}"
        },
        "url": {
          "raw": "{{base_url}}/api/v1/feed/feed/{{post_id}}/",
          "host": ["{{base_url}}"],
          "path": ["api", "v1", "feed", "feed", "{{post_id}}", ""]
        }
      }
    },
    {
      "name": "8. Delete Post",
      "request": {
        "method": "DELETE",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{access_token}}"
          }
        ],
        "url": {
          "raw": "{{base_url}}/api/v1/feed/feed/{{post_id}}/",
          "host": ["{{base_url}}"],
          "path": ["api", "v1", "feed", "feed", "{{post_id}}", ""]
        }
      }
    }
  ]
}
```

### Postman Tips

**Auto-save Response Data:**
Add this to the **Tests** tab of any request:
```javascript
// Save post_id from create post response
if (pm.response.code === 201) {
    var jsonData = pm.response.json();
    pm.collectionVariables.set("post_id", jsonData.data.id);
}
```

**Check Response Status:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Success is true", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.success).to.eql(true);
});
```

---

## Option 2: Use the Automated Test Script

The test script `test_post_menu.py` is currently running and waiting for your credentials.

**Enter your credentials when prompted:**
- Phone number: (your registered phone)
- Password: (your password)

The script will automatically test all endpoints and show results.

---

## Option 2: Manual Testing with cURL

### 1. Get Your Auth Token

```bash
curl -X POST http://127.0.0.1:8000/api/v1/account/login/ -H "Content-Type: application/json" -d "{\"phone\": \"YOUR_PHONE\", \"password\": \"YOUR_PASSWORD\"}"
```

Copy the `access` token from the response.

### 2. Create a Test Post

```bash
curl -X POST http://127.0.0.1:8000/api/v1/feed/feed/ -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" -d "{\"content\": \"Test post\"}"
```

Note the `id` from the response (e.g., `"id": 5`).

### 3. Test Post Owner Actions

**Toggle Comments:**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/feed/feed/5/toggle-comments/ -H "Authorization: Bearer YOUR_TOKEN"
```

**Copy Link:**
```bash
curl -X GET http://127.0.0.1:8000/api/v1/feed/feed/5/copy-link/
```

**Edit Post:**
```bash
curl -X PUT http://127.0.0.1:8000/api/v1/feed/feed/5/ -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" -d "{\"content\": \"Updated content\"}"
```

### 4. Test Viewer Actions

**Mute Post:**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/feed/feed/5/mute/ -H "Authorization: Bearer YOUR_TOKEN"
```

**Report Post:**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/feed/feed/5/report/ -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" -d "{\"reason\": \"spam\", \"description\": \"Test report\"}"
```

**Block User (replace USER_ID):**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/feed/user/USER_ID/block/ -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. Test Comment Restriction

**Disable comments first:**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/feed/feed/5/toggle-comments/ -H "Authorization: Bearer YOUR_TOKEN"
```

**Try to comment (should fail with 403):**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/feed/feed/5/comments/ -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" -d "{\"content\": \"This should fail\"}"
```

---

## Option 3: Test in Django Admin

1. Open browser: `http://127.0.0.1:8000/admin/`
2. Login with your admin credentials
3. Navigate to **Feed** section
4. Check:
   - **Feeds** → Verify `comments_enabled` field
   - **Blocked users** → See blocking relationships
   - **Muted posts** → See muted posts
   - **Reported posts** → Manage reports

---

## Expected Results

### Toggle Comments
```json
{
  "success": true,
  "message": "Comments disabled successfully.",
  "data": {
    "feed_id": 5,
    "comments_enabled": false
  }
}
```

### Copy Link
```json
{
  "success": true,
  "message": "Post link generated successfully.",
  "data": {
    "feed_id": 5,
    "link": "http://127.0.0.1:8000/feed/5/"
  }
}
```

### Mute Post
```json
{
  "success": true,
  "message": "Post muted successfully.",
  "data": {
    "feed_id": 5,
    "is_muted": true
  }
}
```

### Report Post
```json
{
  "success": true,
  "status_code": 201,
  "message": "Post reported successfully. Our team will review it.",
  "data": {
    "id": 1,
    "post_id": 5,
    "reason": "spam",
    "reason_display": "Spam or Misleading",
    "status": "pending"
  }
}
```

### Block User
```json
{
  "success": true,
  "message": "User blocked successfully.",
  "data": {
    "user_id": 3,
    "user_name": "John Doe",
    "is_blocked": true
  }
}
```

### Comment on Disabled Post (Error)
```json
{
  "success": false,
  "status_code": 403,
  "message": "Comments are disabled for this post.",
  "data": []
}
```

---

## Next Steps After Testing

1. ✅ Verify all endpoints work correctly
2. ✅ Check Django admin for created records
3. ✅ Test with different user accounts
4. 📝 Optionally implement feed filtering (blocked/muted posts)
5. 📝 Add notifications for reports/blocks

---

## Troubleshooting

**401 Unauthorized:**
- Check your token is valid
- Token might have expired, login again

**404 Not Found:**
- Verify post ID exists
- Check URL path is correct

**403 Forbidden:**
- For owner actions: ensure you own the post
- For comments: check if comments are enabled

**400 Bad Request:**
- Check request body format
- Verify required fields are provided
- For reports: ensure reason is valid
