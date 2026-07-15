# 🚀 Quick Start - Landing Page

## Get Your Landing Page Running in 5 Minutes

### Step 1: Set Up Stripe (2 minutes)

1. **Create Stripe Account** (if you don't have one)
   - Go to https://stripe.com
   - Sign up / Log in

2. **Create Product**
   - Dashboard → Products → "+ Add Product"
   - Name: "Website Generation Service"
   - Price: $1,000 USD
   - One-time payment

3. **Create Payment Link**
   - Click on your product
   - Click "Create payment link"
   - Copy the link (looks like: `https://buy.stripe.com/xxxxx`)

### Step 2: Add to Environment (30 seconds)

1. Open `.env` file in the root directory
2. Add this line:
   ```
   NEXT_PUBLIC_STRIPE_PAYMENT_LINK=your-copied-stripe-link-here
   ```
3. Save the file

### Step 3: Start the Server (30 seconds)

```bash
npm run dev:web
```

Or if you're in the web directory:
```bash
cd apps/web
npm run dev
```

### Step 4: Test It (1 minute)

1. Open browser: `http://localhost:3000`
2. You'll be redirected to the landing page
3. Scroll through and enjoy the animations!
4. Try filling out the form
5. Click submit to test the Stripe redirect

### Step 5: Customize (optional)

**Change your company name:**
- Open `apps/web/src/app/landing/page.tsx`
- Find "Lenquant" (around line 651)
- Replace with your company name

**Update stats:**
- Find the stats section (around line 143)
- Update numbers to match your business

## That's It!

Your landing page is now live at:
- `http://localhost:3000/landing`
- Root (`/`) automatically redirects there

### Admin Panel Access

Your admin panel is still accessible at:
- `http://localhost:3000/login`
- `http://localhost:3000/nsa`

## What Happens When Someone Orders?

1. Customer fills out form
2. Form data saved via API (check console logs)
3. Customer redirected to Stripe payment
4. Customer pays $1,000
5. Stripe sends them confirmation
6. You receive payment notification from Stripe

## Want to Receive Email Notifications?

Edit `apps/web/src/app/api/leads/route.ts` and add your email service.

Example with SendGrid:
```typescript
import sgMail from '@sendgrid/mail';
sgMail.setApiKey(process.env.SENDGRID_API_KEY!);

await sgMail.send({
  to: 'your-email@company.com',
  from: 'noreply@company.com',
  subject: `New Order: ${body.name}`,
  text: `Name: ${body.name}\nEmail: ${body.email}\n...`,
});
```

## Need Help?

Check the detailed guides:
- `LANDING_PAGE_COMPLETE.md` - Full documentation
- `LANDING_PAGE_SETUP.md` - Detailed setup guide
- `LANDING_PAGE_PREVIEW.md` - Visual structure

## Deploy to Production

When ready to deploy:

1. **Set production environment variable:**
   ```
   NEXT_PUBLIC_STRIPE_PAYMENT_LINK=your-production-stripe-link
   ```

2. **Build:**
   ```bash
   npm run build
   ```

3. **Deploy to your hosting:**
   - Vercel (recommended for Next.js)
   - Netlify
   - AWS
   - Your own server

## Quick Wins

**Increase conversions immediately by:**
1. Adding real client testimonials
2. Adding portfolio images of sites you've built
3. Setting up Google Analytics
4. Creating urgency ("Only 5 slots available this month")
5. Adding live chat widget

Enjoy your new landing page! 🎉
