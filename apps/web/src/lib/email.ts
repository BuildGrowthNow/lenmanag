import { Resend } from "resend";

// Initialize Resend only if API key is available
const resend = process.env.RESEND_API_KEY ? new Resend(process.env.RESEND_API_KEY) : null;

interface NewOrderEmailData {
  name: string;
  email: string;
  company?: string | null;
  phone?: string | null;
  projectDetails: string;
  orderId: string;
  price: number;
  currency: string;
}

export async function sendNewOrderNotification(data: NewOrderEmailData): Promise<boolean> {
  if (!resend) {
    console.warn("Resend API key not configured. Email notification skipped.");
    return false;
  }

  const fromEmail = process.env.RESEND_FROM_EMAIL || "orders@lenquant.com";
  const adminEmail = process.env.RESEND_ADMIN_EMAIL || "fern2gue@gmail.com";
  const appUrl = process.env.NEXT_PUBLIC_APP_URL || "https://sites.lenquant.com";

  try {
    // Send notification to admin
    await resend.emails.send({
      from: fromEmail,
      to: adminEmail,
      subject: `🎉 New Website Order - ${data.name}`,
      html: `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>New Order</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">

  <div style="background: linear-gradient(135deg, #EAB308 0%, #F59E0B 100%); padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px;">
    <h1 style="color: #1E293B; margin: 0; font-size: 28px;">🎉 New Website Order!</h1>
    <p style="color: #334155; margin: 10px 0 0 0; font-size: 16px;">You have a new customer from the landing page</p>
  </div>

  <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
    <h2 style="color: #1E293B; margin: 0 0 16px 0; font-size: 20px; border-bottom: 2px solid #EAB308; padding-bottom: 8px;">Customer Information</h2>

    <table style="width: 100%; border-collapse: collapse;">
      <tr>
        <td style="padding: 8px 0; color: #64748B; width: 120px;"><strong>Name:</strong></td>
        <td style="padding: 8px 0; color: #1E293B;">${data.name}</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; color: #64748B;"><strong>Email:</strong></td>
        <td style="padding: 8px 0; color: #1E293B;"><a href="mailto:${data.email}" style="color: #EAB308; text-decoration: none;">${data.email}</a></td>
      </tr>
      ${data.company ? `
      <tr>
        <td style="padding: 8px 0; color: #64748B;"><strong>Company:</strong></td>
        <td style="padding: 8px 0; color: #1E293B;">${data.company}</td>
      </tr>
      ` : ""}
      ${data.phone ? `
      <tr>
        <td style="padding: 8px 0; color: #64748B;"><strong>Phone:</strong></td>
        <td style="padding: 8px 0; color: #1E293B;"><a href="tel:${data.phone}" style="color: #EAB308; text-decoration: none;">${data.phone}</a></td>
      </tr>
      ` : ""}
      <tr>
        <td style="padding: 8px 0; color: #64748B;"><strong>Order Value:</strong></td>
        <td style="padding: 8px 0; color: #1E293B; font-weight: bold; font-size: 18px; color: #16A34A;">$${data.price.toFixed(2)} ${data.currency}</td>
      </tr>
    </table>
  </div>

  <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
    <h2 style="color: #92400E; margin: 0 0 12px 0; font-size: 18px;">📋 Project Details</h2>
    <p style="color: #78350F; margin: 0; white-space: pre-wrap; line-height: 1.6;">${data.projectDetails}</p>
  </div>

  <div style="background: #F1F5F9; border-radius: 12px; padding: 20px; margin-bottom: 24px; text-align: center;">
    <p style="margin: 0 0 16px 0; color: #475569;">View and manage this order in your admin panel:</p>
    <a href="${appUrl}/nsa/orders"
       style="display: inline-block; background: #EAB308; color: #1E293B; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">
      View Order Details
    </a>
  </div>

  <div style="border-top: 2px solid #E2E8F0; padding-top: 20px; text-align: center;">
    <p style="color: #94A3B8; font-size: 14px; margin: 0;">
      Order ID: <code style="background: #F1F5F9; padding: 2px 6px; border-radius: 4px; font-size: 12px;">${data.orderId}</code>
    </p>
    <p style="color: #94A3B8; font-size: 14px; margin: 8px 0 0 0;">
      Received at ${new Date().toLocaleString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })}
    </p>
  </div>

  <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid #E2E8F0; text-align: center;">
    <p style="color: #64748B; font-size: 13px; margin: 0;">
      <strong style="color: #1E293B;">Lenquant</strong> - Premium websites delivered in 3 days
    </p>
    <p style="color: #94A3B8; font-size: 12px; margin: 8px 0 0 0;">
      This is an automated notification from your landing page order system.
    </p>
  </div>

</body>
</html>
      `,
    });

    console.log("Order notification email sent successfully to:", adminEmail);
    return true;
  } catch (error) {
    console.error("Failed to send order notification email:", error);
    return false;
  }
}

interface CustomerConfirmationEmailData {
  name: string;
  email: string;
  orderId: string;
}

export async function sendCustomerConfirmation(data: CustomerConfirmationEmailData): Promise<boolean> {
  if (!resend) {
    console.warn("Resend API key not configured. Confirmation email skipped.");
    return false;
  }

  const fromEmail = process.env.RESEND_FROM_EMAIL || "orders@lenquant.com";

  try {
    await resend.emails.send({
      from: fromEmail,
      to: data.email,
      subject: "Thank you for your order - Lenquant",
      html: `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Order Confirmation</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">

  <div style="background: linear-gradient(135deg, #EAB308 0%, #F59E0B 100%); padding: 40px 30px; border-radius: 12px; text-align: center; margin-bottom: 30px;">
    <h1 style="color: #1E293B; margin: 0; font-size: 32px;">✨ Thank You, ${data.name}!</h1>
    <p style="color: #334155; margin: 16px 0 0 0; font-size: 18px; line-height: 1.5;">We've received your website project request</p>
  </div>

  <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
    <h2 style="color: #1E293B; margin: 0 0 16px 0; font-size: 20px;">What Happens Next?</h2>
    <div style="margin-bottom: 16px;">
      <div style="display: flex; align-items: start; margin-bottom: 16px;">
        <div style="background: #EAB308; color: #1E293B; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 16px; flex-shrink: 0;">1</div>
        <div>
          <h3 style="margin: 0 0 4px 0; color: #1E293B; font-size: 16px;">We'll Review Your Request</h3>
          <p style="margin: 0; color: #64748B; font-size: 14px;">Our team will review your project details within 24 hours</p>
        </div>
      </div>
      <div style="display: flex; align-items: start; margin-bottom: 16px;">
        <div style="background: #EAB308; color: #1E293B; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 16px; flex-shrink: 0;">2</div>
        <div>
          <h3 style="margin: 0 0 4px 0; color: #1E293B; font-size: 16px;">Payment & Kickoff</h3>
          <p style="margin: 0; color: #64748B; font-size: 14px;">Once payment is confirmed, we'll start your 3-day delivery timeline</p>
        </div>
      </div>
      <div style="display: flex; align-items: start;">
        <div style="background: #EAB308; color: #1E293B; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 16px; flex-shrink: 0;">3</div>
        <div>
          <h3 style="margin: 0 0 4px 0; color: #1E293B; font-size: 16px;">Receive Your Website</h3>
          <p style="margin: 0; color: #64748B; font-size: 14px;">Get your complete, production-ready website in just 3 days</p>
        </div>
      </div>
    </div>
  </div>

  <div style="background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
    <p style="margin: 0; color: #065F46; font-size: 15px; line-height: 1.6;">
      <strong>📧 Check your inbox:</strong> We'll send you an email within 24 hours with next steps and payment details.
    </p>
  </div>

  <div style="background: #F1F5F9; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
    <h3 style="color: #1E293B; margin: 0 0 12px 0; font-size: 16px;">Your Order Reference</h3>
    <p style="margin: 0; color: #64748B; font-size: 14px;">
      Order ID: <code style="background: #FFF; padding: 4px 8px; border-radius: 4px; border: 1px solid #E2E8F0;">${data.orderId}</code>
    </p>
    <p style="margin: 12px 0 0 0; color: #64748B; font-size: 13px;">
      Save this reference number for your records.
    </p>
  </div>

  <div style="text-align: center; padding: 20px 0;">
    <p style="color: #64748B; font-size: 15px; margin: 0 0 12px 0;">Questions? We're here to help!</p>
    <p style="margin: 0;">
      <a href="mailto:fern2gue@gmail.com" style="color: #EAB308; text-decoration: none; font-weight: 600;">fern2gue@gmail.com</a>
    </p>
  </div>

  <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid #E2E8F0; text-align: center;">
    <p style="color: #64748B; font-size: 14px; margin: 0;">
      <strong style="color: #1E293B;">Lenquant</strong>
    </p>
    <p style="color: #94A3B8; font-size: 12px; margin: 8px 0;">
      Premium websites delivered in 3 days or less
    </p>
  </div>

</body>
</html>
      `,
    });

    console.log("Confirmation email sent successfully to:", data.email);
    return true;
  } catch (error) {
    console.error("Failed to send confirmation email:", error);
    return false;
  }
}
