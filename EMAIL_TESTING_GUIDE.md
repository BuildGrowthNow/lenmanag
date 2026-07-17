# Email System Testing Guide

## 🎉 Complete Implementation Summary

Successfully implemented enhanced post-payment email system with:

### Customer Email Features:
- ✅ Payment confirmation with itemized order breakdown
- ✅ Calendly booking CTA (https://calendly.com/lenquant/sites)
- ✅ 3-step timeline (Book → Kickoff within 48h → Delivery in 3 days)
- ✅ Contact: pedro@lenquant.com & +1 (845) 721-1974
- ✅ 4-hour response promise (business hours)
- ✅ Monthly recurring service notifications

### Team Email Features:
- ✅ Sent to 4 recipients: fern2gue@gmail.com, fernando@lenquant.com, pedro@lenquant.com, pedrocdiegues@gmail.com
- ✅ Subject includes order value ($X,XXX)
- ✅ ACTION REQUIRED banner (4-hour window)
- ✅ Full itemized breakdown with billing cycles
- ✅ Next steps checklist
- ✅ Link to /app/orders

---

## 📧 How to Send Test Emails

### Step 1: Wait for Deployment
GitHub Actions will deploy automatically in ~5 minutes after push.

### Step 2: SSH into Production Server
```bash
ssh -i C:\Users\smikl\.ssh\lenquant.pem ubuntu@ec2-32-194-123-142.compute-1.amazonaws.com
```

### Step 3: Navigate to Web Directory
```bash
cd /opt/lenquant/apps/web
```

### Step 4: Send Test Emails
```bash
bash send-test-email.sh
```

This sends:
- **Team email** → All 4 team members
- **Customer email** → john.smith@example.com (test)

Example order: **$1,950**
- Professional Website: $1,000
- 5 Additional Pages: $250 ($50 × 5)
- Maintenance Service: $500/month
- Hosting Service: $200/month
- **Monthly recurring: $700/month**

---

## ✅ Verification Checklist

### Customer Email Check:
- [ ] Subject: "✅ Payment Received - Let's Schedule Your Kickoff Call!"
- [ ] Green header with "Payment Confirmed"
- [ ] Order summary table with 4 line items
- [ ] Total: $1,950
- [ ] Yellow Calendly button (https://calendly.com/lenquant/sites)
- [ ] Monthly badge shows $700/month
- [ ] Contact: pedro@lenquant.com and +1 (845) 721-1974
- [ ] 3-step timeline visible
- [ ] Professional design, no broken formatting

### Team Email Check:
- [ ] Subject: "🎉 NEW PAID ORDER - $1,950 - John Smith"
- [ ] All 4 emails in TO field
- [ ] "ACTION REQUIRED" yellow banner
- [ ] Order details table with line items
- [ ] Customer info: email, phone, company
- [ ] Monthly recurring note ($700/month)
- [ ] "View Order Details" button links to /app/orders
- [ ] Next steps checklist (5 steps)
- [ ] Professional design, no broken formatting

---

## 🚀 Live Production Flow

When a real customer pays:

1. **Customer completes Stripe checkout** → Payment processed
2. **Stripe webhook fires** → `/api/webhook/stripe`
3. **Database updated** → `paymentStatus: "paid"`
4. **Two emails sent automatically:**
   - Customer → Calendly booking email
   - Team (4 inboxes) → New order notification
5. **Customer books call** (or team reaches out within 4 hours)
6. **Kickoff call** (within 48 hours)
7. **Website delivered** (3 days)

---

## 🔧 Troubleshooting

### Emails not sending?
Check environment variables on server:
```bash
cat /opt/lenquant/.env.production | grep RESEND
```

Should have:
- `RESEND_API_KEY=re_...`
- `RESEND_FROM_EMAIL=orders@lenquant.com`

### Test script fails?
1. Ensure `tsx` is installed: `npm install -g tsx`
2. Check you're in `/opt/lenquant/apps/web` directory
3. Verify .env.production exists in `/opt/lenquant/`

### Emails go to spam?
1. Check Resend dashboard for delivery status
2. Verify SPF/DKIM records for lenquant.com domain
3. Ask recipients to whitelist orders@lenquant.com

---

## 📁 Modified Files

- `apps/web/src/lib/email.ts` — Email templates with line items
- `apps/web/src/app/api/webhook/stripe/route.ts` — Pass lineItems to emails
- `apps/web/src/app/api/leads/route.ts` — Updated for new email signature
- `apps/web/test-emails.ts` — Test script (new)
- `apps/web/send-test-email.sh` — Server test runner (new)

---

## 🎯 Next Steps

1. ✅ Wait for deployment (~5 minutes)
2. ✅ Run test email script on server
3. ✅ Verify all 4 team members receive team email
4. ✅ Verify customer email looks professional
5. ✅ Test Calendly link (https://calendly.com/lenquant/sites)
6. ✅ Confirm contact info is correct
7. ✅ Ready for production! 🚀
