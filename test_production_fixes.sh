#!/bin/bash
# Test script to verify production fixes
# Run this after both backend and frontend are running

set -e

echo "🔧 Testing Production Fixes"
echo "=============================="
echo ""

# Configuration
BACKEND_URL="http://localhost:8000"
API_BASE="${BACKEND_URL}/api/v1"

# Step 1: Login and get session
echo "📝 Step 1: Login..."
LOGIN_RESPONSE=$(curl -s -c /tmp/cookies.txt -X POST "${API_BASE}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "fern2gue@gmail.com", "password": "LENGROWTH2026"}')

# Extract session cookie
SESSION=$(grep lenquant_session /tmp/cookies.txt 2>/dev/null | awk '{print $NF}' || echo "")

if [ -z "$SESSION" ]; then
  echo "❌ Login failed. Response:"
  echo "$LOGIN_RESPONSE"
  exit 1
fi

echo "✅ Logged in successfully"
echo ""

# Step 2: Create a test lead
echo "📝 Step 2: Creating test lead..."
LEAD_RESPONSE=$(curl -s -b /tmp/cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Test Lead",
    "email": "test@example.com",
    "companyName": "Test Company",
    "websiteUrl": "https://example.com",
    "industry": "Technology",
    "targetAudience": "Business users",
    "notes": "Test lead for production fix verification"
  }' \
  "${API_BASE}/leads")

LEAD_ID=$(echo "$LEAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('data', {}).get('lead', {}).get('id', ''))" 2>/dev/null || echo "")

if [ -z "$LEAD_ID" ]; then
  echo "❌ Failed to create lead. Response:"
  echo "$LEAD_RESPONSE"
  exit 1
fi

echo "✅ Created lead: $LEAD_ID"
echo ""

echo "🎉 Test Infrastructure Ready"
echo "   Lead ID: $LEAD_ID"
echo "   Use this ID to test the reported issues manually"
