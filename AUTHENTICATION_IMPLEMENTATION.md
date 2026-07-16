# Authentication System Implementation Summary

## Overview
A production-ready authentication system has been implemented using JWT tokens, MongoDB for user storage, bcrypt for password hashing, and Resend for email verification. The system replaces the old session-based auth with a proper user management system.

## Backend Changes

### New Files Created
1. **`apps/backend/app/schemas/user.py`** - User schemas for signup, login, and responses
2. **`apps/backend/app/core/users.py`** - UserRepository for user CRUD operations
3. **`apps/backend/app/core/jwt_handler.py`** - JWT token creation and validation
4. **`apps/backend/app/core/email_service.py`** - Email verification using Resend
5. **`apps/backend/app/core/auth_dependencies.py`** - FastAPI dependencies for authentication
6. **`apps/backend/app/api/users.py`** - User API endpoints (signup, login, verify-email, etc.)

### Modified Files
1. **`apps/backend/app/core/config.py`** - Added JWT and signup code configuration
2. **`apps/backend/app/api/router.py`** - Registered users router
3. **`apps/backend/app/api/leads.py`** - Updated to use JWT auth and pass user_id
4. **`apps/backend/app/core/leads.py`** - Added user_id to lead creation and filtering
5. **`apps/backend/app/schemas/lead.py`** - Added user_id field to LeadListItem and LeadDetail
6. **`apps/backend/app/schemas/message.py`** - Added user_id field to MessageDraft
7. **`apps/backend/pyproject.toml`** - Added dependencies: pyjwt, bcrypt, resend

### Database Schema
MongoDB `users` collection:
```javascript
{
  "_id": ObjectId,
  "email": string (unique, lowercase),
  "hashed_password": string (bcrypt),
  "is_verified": boolean,
  "verification_token": string (nullable),
  "created_at": datetime,
  "updated_at": datetime
}
```

All leads, sites, and messages now include a `user_id` field to associate data with the creating user.

### API Endpoints

#### Authentication Endpoints
- `POST /api/v1/users/signup` - Create new user account (requires signup code)
- `POST /api/v1/users/login` - Login and receive JWT token
- `POST /api/v1/users/verify-email` - Verify email with token
- `POST /api/v1/users/resend-verification` - Resend verification email
- `GET /api/v1/users/me` - Get current user info

#### Updated Lead Endpoints
All lead endpoints now require JWT authentication via Authorization header:
- Leads are filtered by user_id automatically
- Users can only see/edit their own leads

## Frontend Changes

### New Files Created
1. **`apps/web/src/lib/api/users.ts`** - User API client functions
2. **`apps/web/src/app/signup/page.tsx`** - Signup page with signup code field
3. **`apps/web/src/app/verify-email/page.tsx`** - Email verification page

### Modified Files
1. **`apps/web/src/app/login/login-form.tsx`** - Updated to use new auth API
2. **`apps/web/src/middleware.ts`** - Updated to handle JWT and new auth routes
3. **`apps/web/src/lib/api/client.ts`** - Added Authorization header from localStorage
4. **`apps/web/src/lib/routes.ts`** - Changed all routes from /nsa to /app
5. **`apps/web/package.json`** - Added @supabase/supabase-js and react-error-boundary

### Route Changes
All dashboard routes changed from `/nsa/*` to `/app/*`:
- `/nsa` → `/app`
- `/nsa/leads` → `/app/leads`
- `/nsa/sites` → `/app/sites`
- etc.

## Configuration

### Environment Variables (.env)
```bash
# JWT Authentication
JWT_SECRET=replace-with-a-secure-random-string-for-jwt
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=168  # 7 days

# Signup Code (required for new signups)
SIGNUP_CODE=your-secret-signup-code-here

# Email Service (Resend)
RESEND_API_KEY=re_your_api_key_here
RESEND_FROM_EMAIL=noreply@lenquant.com
```

## Authentication Flow

### 1. Signup Flow
1. User visits `/signup` and enters email, password, and signup code
2. Backend validates signup code from .env
3. Backend creates user with hashed password using bcrypt
4. Backend generates verification token and stores it
5. Backend sends verification email via Resend
6. Backend returns JWT token immediately (user can use app while unverified)
7. User clicks link in email to verify account

### 2. Login Flow
1. User visits `/login` and enters email and password
2. Backend verifies password using bcrypt
3. Backend generates JWT token (7-day expiry)
4. Frontend stores token in localStorage
5. Frontend redirects to `/app`

### 3. API Request Flow
1. Frontend includes `Authorization: Bearer <token>` header in all API requests
2. Backend validates JWT token and extracts user_id
3. Backend filters/creates data with user_id
4. Only user's own data is accessible

## Security Features

1. **Password Hashing**: bcrypt with salt
2. **JWT Tokens**: Signed with secret, 7-day expiry
3. **Signup Code Protection**: Prevents unauthorized registrations
4. **Email Verification**: Confirms email ownership
5. **User Data Isolation**: Users can only access their own leads/sites/messages
6. **HTTPS Only**: SESSION_COOKIE_SECURE=true for production

## Migration Notes

### For Existing Users
- Old session-based authentication is deprecated
- Existing users need to sign up with new system
- Old leads without user_id will not be visible (need migration script if preserving data)

### For Deployment
1. Set all environment variables in production
2. Generate secure JWT_SECRET: `openssl rand -base64 32`
3. Set SIGNUP_CODE to prevent open signups
4. Configure Resend API for email sending
5. Update CORS settings if frontend/backend on different domains

## Testing

### Backend
```bash
cd apps/backend
python -m pytest tests/  # (create tests for new endpoints)
```

### Frontend
```bash
cd apps/web
npm run lint
npm run build
```

## Future Improvements

1. Add password reset functionality
2. Add email change with verification
3. Add 2FA/MFA support
4. Add OAuth providers (Google, GitHub, etc.)
5. Add user profile management
6. Add session management (logout all devices)
7. Add rate limiting on auth endpoints
8. Create migration script for existing data

## Troubleshooting

### "Invalid signup code"
- Check SIGNUP_CODE in .env matches what user entered
- Check .env is loaded properly

### "Email already registered"
- User already exists, use /login instead

### "Invalid or expired verification token"
- Link may have expired, use resend-verification endpoint

### "Authentication required" on API calls
- Check JWT token is in localStorage
- Check Authorization header is being sent
- Check token hasn't expired (7 days)

### Leads not showing up
- Leads are filtered by user_id
- Old leads without user_id won't show
- Check user is logged in with correct account
