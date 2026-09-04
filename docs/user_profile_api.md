# User Profile API Documentation

This document outlines the User Profile & Preferences API (Phase 10.2).
The endpoints allow fetching and updating the authenticated user's profile information.

## Endpoints

### 1. Get User Profile

Retrieve the profile for the currently authenticated user.

- **URL:** `/api/v1/profile`
- **Method:** `GET`
- **Authentication Required:** Yes (Bearer Token)

**Success Response (200 OK):**
```json
{
  "id": "uuid-string",
  "user_id": "auth-user-id",
  "name": "John Doe",
  "avatar": "base64-string",
  "bio": "Software Engineer",
  "timezone": "UTC",
  "theme_preference": "dark",
  "preferred_llm_provider": "openai",
  "default_ai_model": "gpt-4o",
  "notification_preferences": {
    "email": true,
    "in_app": true
  },
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing token.

---

### 2. Update User Profile

Update the profile for the currently authenticated user. All fields in the request body are optional.

- **URL:** `/api/v1/profile`
- **Method:** `PUT`
- **Authentication Required:** Yes (Bearer Token)

**Request Body (JSON):**
```json
{
  "name": "Jane Doe",
  "bio": "Senior AI Engineer",
  "theme_preference": "light",
  "timezone": "America/New_York"
}
```
*Note: You only need to send the fields you wish to update.*

**Success Response (200 OK):**
Returns the complete updated User Profile object.
```json
{
  "id": "uuid-string",
  "user_id": "auth-user-id",
  "name": "Jane Doe",
  "avatar": "base64-string",
  "bio": "Senior AI Engineer",
  "timezone": "America/New_York",
  "theme_preference": "light",
  "preferred_llm_provider": "openai",
  "default_ai_model": "gpt-4o",
  "notification_preferences": {
    "email": true,
    "in_app": true
  },
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-02T15:30:00Z"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing token.
- `422 Unprocessable Entity`: Invalid request payload.
