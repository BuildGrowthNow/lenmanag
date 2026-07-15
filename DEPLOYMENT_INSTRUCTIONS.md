# 🚀 Deployment Instructions - sites.lenquant.com

## Quick Start

Your landing page is **production-ready** and can be deployed immediately.

## Required Environment Variables

Set these in your production environment:

```bash
# MongoDB (Required)
MONGODB_URI=mongodb+srv://fern2gue:hJk7CDkZuwssFDz4@lenmanag.zzbkrv.mongodb.net/
MONGODB_DB_NAME=lenmanag

# Stripe Payment (Required)
NEXT_PUBLIC_STRIPE_PAYMENT_LINK=https://buy.stripe.com/your-payment-link

# Application URLs (Required)
NEXT_PUBLIC_APP_URL=https://sites.lenquant.com

# Authentication (For admin panel)
SESSION_SECRET=your-secure-random-string-here
AUTH_ALLOWLIST_EMAILS=fern2gue@gmail.com,admin@lenquant.com
AUTH_ALLOWLIST_DOMAINS=lenquant.com,lengrowth.com,sites.lenquant.com
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
SESSION_COOKIE_DOMAIN=.lenquant.com
SESSION_COOKIE_MAX_AGE_SECONDS=28800
```

## Deploy to Vercel (Recommended)

### Step 1: Install Vercel CLI
```bash
npm install -g vercel
```

### Step 2: Login to Vercel
```bash
vercel login
```

### Step 3: Deploy
```bash
cd apps/web
vercel --prod
```

### Step 4: Set Environment Variables
1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your project
3. Go to **Settings** → **Environment Variables**
4. Add all variables from above
5. Redeploy: `vercel --prod`

### Step 5: Configure Domain
1. In Vercel Dashboard → **Settings** → **Domains**
2. Add `sites.lenquant.com`
3. Follow DNS instructions to point domain
4. SSL will be auto-configured

## Alternative: Deploy to AWS/VPS

### Using Docker

1. **Build the Docker image:**
```bash
cd apps/web
docker build -t lenquant-landing .
```

2. **Run the container:**
```bash
docker run -d \
  --name lenquant-landing \
  -p 3000:3000 \
  -e MONGODB_URI="mongodb+srv://..." \
  -e MONGODB_DB_NAME="lenmanag" \
  -e NEXT_PUBLIC_STRIPE_PAYMENT_LINK="https://buy.stripe.com/..." \
  -e NEXT_PUBLIC_APP_URL="https://sites.lenquant.com" \
  -e SESSION_SECRET="your-secret" \
  lenquant-landing
```

3. **Set up Nginx reverse proxy:**
```nginx
server {
    listen 80;
    server_name sites.lenquant.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

4. **Get SSL certificate:**
```bash
sudo certbot --nginx -d sites.lenquant.com
```

## Stripe Setup

### Step 1: Create Product
1. Go to [Stripe Dashboard](https://dashboard.stripe.com)
2. Navigate to **Products** → **Add Product**
3. Name: "Website Generation Service"
4. Price: $1,000 USD (one-time)

### Step 2: Create Payment Link
1. Click **Create Payment Link**
2. Select the product
3. Enable **Collect customer information** (name, email)
4. Copy the payment link

### Step 3: Update Environment
```bash
NEXT_PUBLIC_STRIPE_PAYMENT_LINK=https://buy.stripe.com/[your-link-here]
```

### Step 4: Test Mode First
- Use test mode initially
- Process test payments
- Verify webhooks work
- Switch to live mode when ready

## Database Setup

Your MongoDB is already configured. To add indexes for better performance:

```javascript
// Connect to MongoDB Atlas
use lenmanag;

// Create indexes
db.leads.createIndex({ createdAt: -1 });
db.leads.createIndex({ email: 1 });
db.leads.createIndex({ status: 1 });
```

## Post-Deployment Testing

### Critical Tests
- [ ] Visit https://sites.lenquant.com → Should show landing page
- [ ] Submit form with valid data → Should save to MongoDB
- [ ] Click "Start Your Project Now" → Should open Stripe payment
- [ ] Check mobile responsiveness → Works on all devices
- [ ] Test on multiple browsers → Chrome, Safari, Firefox, Edge

### SEO Tests
- [ ] Visit https://sites.lenquant.com/sitemap.xml → Should show sitemap
- [ ] Visit https://sites.lenquant.com/robots.txt → Should show robots.txt
- [ ] Run Lighthouse audit → Score > 90
- [ ] Check meta tags in source → Should include title, description, OG tags

### Database Tests
- [ ] Submit a form → Check MongoDB for new lead
- [ ] Verify timestamps are correct
- [ ] Check all fields are saved properly

## Monitoring

### View Leads
- Go to https://sites.lenquant.com/nsa/leads
- Requires authentication
- See all submitted forms

### MongoDB Monitoring
- MongoDB Atlas dashboard
- Monitor query performance
- Set up alerts for failures

### Application Logs
**Vercel:**
- View logs in dashboard
- Real-time streaming
- Error tracking

**VPS/AWS:**
```bash
docker logs -f lenquant-landing
```

## Maintenance

### Daily
- Check new leads in admin panel
- Respond to inquiries within 24 hours

### Weekly
- Review form analytics
- Check for errors in logs
- Test payment link still works

### Monthly
- Update dependencies: `npm update`
- Review MongoDB storage usage
- Check SSL certificate expiry

## Troubleshooting

### Form Not Submitting
1. Check browser console for errors
2. Verify `MONGODB_URI` is set correctly
3. Check MongoDB Atlas network access (allow all IPs)
4. Test API endpoint: `curl -X POST https://sites.lenquant.com/api/leads`

### Payment Link Not Working
1. Verify `NEXT_PUBLIC_STRIPE_PAYMENT_LINK` is set
2. Check Stripe dashboard for link status
3. Ensure link is in live mode (not test mode)

### Page Not Loading
1. Check deployment logs
2. Verify environment variables are set
3. Check DNS propagation: `dig sites.lenquant.com`
4. Verify SSL certificate is valid

### MongoDB Connection Error
1. Check MongoDB Atlas is running
2. Verify IP whitelist includes your server
3. Check connection string format
4. Test connection: `mongosh "mongodb+srv://..."`

## Support

For deployment issues:
- Email: fern2gue@gmail.com
- Check logs first
- Provide error messages
- Include browser/environment details

## Security Checklist

- [ ] SSL/HTTPS enabled
- [ ] MongoDB uses authentication
- [ ] Session secret is secure random string
- [ ] CORS configured properly
- [ ] No sensitive data in client code
- [ ] Environment variables not committed to git
- [ ] Rate limiting enabled (optional)
- [ ] CAPTCHA added if spam becomes issue (optional)

## Performance Checklist

- [ ] Images optimized
- [ ] Animations are GPU-accelerated
- [ ] No console errors
- [ ] Lighthouse score > 90
- [ ] First Contentful Paint < 1.5s
- [ ] Time to Interactive < 3s

## SEO Checklist

- [x] Meta tags configured
- [x] Sitemap generated
- [x] Robots.txt present
- [x] Structured data added
- [x] Open Graph tags
- [ ] Google Analytics added (optional)
- [ ] Google Search Console verified (optional)

---

## Ready to Deploy! ✅

Your landing page is fully production-ready. Follow the steps above to deploy.

**Estimated deployment time:** 15-30 minutes

**Domains ready:**
- Production: sites.lenquant.com
- Landing: sites.lenquant.com/landing
- Admin: sites.lenquant.com/nsa

**Files changed:**
- Landing page: `/apps/web/src/app/landing/page.tsx`
- API route: `/apps/web/src/app/api/leads/route.ts`
- MongoDB lib: `/apps/web/src/lib/mongodb.ts`
- Sitemap: `/apps/web/src/app/sitemap.ts`
- Robots: `/apps/web/public/robots.txt`
- Layout: `/apps/web/src/app/landing/layout.tsx`

**Build status:** ✅ Successful (no errors)
**Lint status:** ✅ Passed (1 unrelated warning)
**Production ready:** ✅ YES
