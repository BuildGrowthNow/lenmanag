# 📧 Resend Email Setup Guide

## Quick Setup (5 minutes)

### Step 1: Create Resend Account

1. Go to https://resend.com
2. Click "Sign Up"
3. Use your email (fern2gue@gmail.com)
4. Verify your email

### Step 2: Get API Key

1. Once logged in, go to **API Keys** section
2. Click "Create API Key"
3. Name it: "Lenquant Production"
4. Click "Add"
5. **Copy the key immediately** (shown only once!)

Example: `re_123abc456def...`

### Step 3: Add to Environment Variables

#### Local Development (.env)
```bash
RESEND_API_KEY=re_your_actual_key_here
RESEND_FROM_EMAIL=orders@lenquant.com
RESEND_ADMIN_EMAIL=fern2gue@gmail.com
```

#### Production (Vercel/Hosting)
Add the same variables to your hosting environment.

### Step 4: Test Emails (Optional but Recommended)

For now, Resend will send from their domain:
- From: `orders@lenquant.com via resend.dev`

To remove "via resend.dev":
1. Add your domain in Resend
2. Add DNS records they provide
3. Wait for verification (a few minutes)

### Step 5: Verify It Works

1. Submit a test order on your landing page
2. Check your email (fern2gue@gmail.com)
3. You should receive "🎉 New Website Order"

---

## Domain Setup (Optional - Better Deliverability)

### Why Add a Domain?
- Emails look more professional
- Better deliverability
- No "via resend.dev" tag
- Higher trust from email providers

### How to Add Domain

1. **In Resend Dashboard:**
   - Go to "Domains"
   - Click "Add Domain"
   - Enter: `lenquant.com`

2. **Add DNS Records:**
   Resend will show you DNS records to add. Example:

   ```
   Type: TXT
   Name: _resend
   Value: resend-verify=abc123...
   
   Type: CNAME
   Name: resend._domainkey
   Value: resend._domainkey.lenquant.com
   ```

3. **Add to Your DNS Provider:**
   (Wherever lenquant.com is hosted - Cloudflare, GoDaddy, etc.)

4. **Wait for Verification:**
   - Usually takes 5-15 minutes
   - Resend will show "Verified" when ready

5. **Update Environment Variable:**
   ```bash
   RESEND_FROM_EMAIL=orders@lenquant.com
   ```

---

## Email Templates

### Admin Notification (What You Receive)

```
Subject: 🎉 New Website Order - John Doe

Customer Information:
- Name: John Doe
- Email: john@example.com
- Company: Acme Inc
- Phone: +1 555-0123
- Order Value: $1,000 USD

Project Details:
[Customer's project description]

[View Order Details Button]
```

### Customer Confirmation (What They Receive)

```
Subject: Thank you for your order - Lenquant

Thank You, John!
We've received your website project request

What Happens Next?
1. We'll Review Your Request (24 hours)
2. Payment & Kickoff
3. Receive Your Website (3 days)

Your Order Reference: 507f1f77bcf86cd799439011
```

---

## Troubleshooting

### Not Receiving Emails?

**Check 1: API Key Set?**
```bash
# In your terminal
echo $RESEND_API_KEY
```

**Check 2: Check Spam Folder**
- Emails might be in spam first time
- Mark as "Not Spam"

**Check 3: Check Resend Logs**
- Go to Resend Dashboard → Logs
- See if emails were sent
- Check for errors

**Check 4: Environment Variables**
- Make sure `.env` file exists
- Restart your dev server after adding env vars

**Check 5: Console Logs**
```bash
# In server logs, look for:
"Order notification email sent successfully"
"Confirmation email sent successfully"
```

### Emails Going to Spam?

1. **Add Custom Domain** (see above)
2. **Add SPF Record**
   ```
   Type: TXT
   Name: @
   Value: v=spf1 include:resend.com ~all
   ```
3. **Add DMARC Record**
   ```
   Type: TXT
   Name: _dmarc
   Value: v=DMARC1; p=none; rua=mailto:fern2gue@gmail.com
   ```

### Rate Limits

**Free Tier:**
- 100 emails/day
- 3,000 emails/month

If you hit limits:
- Upgrade to paid plan ($20/month for 50k emails)
- Or implement email queuing

---

## Testing in Development

### 1. Using Real Emails
```bash
RESEND_API_KEY=re_real_key
RESEND_ADMIN_EMAIL=fern2gue@gmail.com
```

Submit form → Emails sent to real addresses

### 2. Using Test Mode
```bash
RESEND_API_KEY=re_test_key
```

Resend captures emails but doesn't send them.
View in Resend Dashboard.

---

## Production Checklist

- [ ] Resend account created
- [ ] API key generated
- [ ] Environment variables set in production
- [ ] Test order submitted
- [ ] Admin email received
- [ ] Customer email received
- [ ] Emails display correctly on mobile
- [ ] Domain verified (optional)
- [ ] DNS records added (optional)

---

## Pricing

### Free Tier
- 100 emails/day
- 3,000 emails/month
- Perfect for starting out

### Paid Plans
- **Pro**: $20/month for 50,000 emails
- **Scale**: Custom pricing

Most users start with Free tier.

---

## Support

**Resend Documentation:**
https://resend.com/docs

**Resend Support:**
support@resend.com

**Your Support:**
fern2gue@gmail.com

---

## Example Working Configuration

```bash
# .env file
MONGODB_URI=mongodb+srv://fern2gue:hJk7CDkZuwssFDz4@lenmanag.zzbkrv.mongodb.net/
MONGODB_DB_NAME=lenmanag
NEXT_PUBLIC_STRIPE_PAYMENT_LINK=https://buy.stripe.com/test_abc123
NEXT_PUBLIC_APP_URL=https://sites.lenquant.com
RESEND_API_KEY=re_abc123def456
RESEND_FROM_EMAIL=orders@lenquant.com
RESEND_ADMIN_EMAIL=fern2gue@gmail.com
```

---

## Quick Commands

### Test Email Locally
```bash
# Start dev server
npm run dev

# Submit form at http://localhost:3000
# Check console logs for email status
```

### Check Email in Production
```bash
# Check Vercel logs
vercel logs

# Look for:
"Order notification email sent"
```

---

That's it! You're ready to receive beautiful email notifications for every new order. 🎉
