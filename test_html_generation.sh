#!/bin/bash

# Test HTML variant generation for jarutter.com lead
# This will trigger generation and we can check logs

API_BASE="https://sites-api.lenquant.com/api/v1"

echo "=== Testing HTML Variant Generation ==="
echo ""

# Step 1: Login to get session
echo "Step 1: Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "fern2gue@gmail.com", "password": "LENGROWTH2026"}')

SESSION=$(echo "$LOGIN_RESPONSE" | grep -o '"lenquant_session":"[^"]*"' | cut -d'"' -f4)

if [ -z "$SESSION" ]; then
  echo "ERROR: Failed to get session token"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "✓ Logged in successfully"
echo ""

# Step 2: Get existing lead for jarutter.com
echo "Step 2: Finding jarutter.com lead..."
LEADS_RESPONSE=$(curl -s -H "Cookie: lenquant_session=$SESSION" \
  "$API_BASE/leads?limit=50")

LEAD_ID=$(echo "$LEADS_RESPONSE" | grep -o '"websiteUrl":"https://jarutter.com"' -A 10 | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$LEAD_ID" ]; then
  echo "ERROR: Could not find jarutter.com lead"
  echo "Response: $LEADS_RESPONSE"
  exit 1
fi

echo "✓ Found lead: $LEAD_ID"
echo ""

# Step 3: Trigger site generation with force flag
echo "Step 3: Triggering site generation (force=true)..."
GEN_RESPONSE=$(curl -s -X POST -H "Cookie: lenquant_session=$SESSION" \
  -H "Content-Type: application/json" \
  -d '{"force": true}' \
  "$API_BASE/sites/$LEAD_ID/generate")

echo "Generation triggered:"
echo "$GEN_RESPONSE" | head -50
echo ""

# Step 4: Wait a bit for generation to complete
echo "Step 4: Waiting 30 seconds for generation..."
sleep 30

# Step 5: Check logs on server
echo ""
echo "Step 5: Checking backend logs for debug output..."
echo "=========================================="
ssh -i /c/Users/smikl/.ssh/lenquant.pem ubuntu@ec2-32-194-123-142.compute-1.amazonaws.com \
  "cd /opt/lenquant && docker compose logs --tail=100 backend | grep -E 'DEBUG|static HTML|Generating|Parsed|S3 upload'"

echo ""
echo "=========================================="
echo "Check complete. Review logs above for debug output."
