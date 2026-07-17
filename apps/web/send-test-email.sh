#!/bin/bash

# Test script to send example order notification emails
# Run this on the production server where .env.production exists

cd /opt/lenquant/apps/web

# Load production environment variables
export $(cat /opt/lenquant/.env.production | grep RESEND | xargs)

# Run the test email script
npx tsx test-emails.ts
