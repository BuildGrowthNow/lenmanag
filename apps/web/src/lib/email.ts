import { Resend } from "resend";

// Initialize Resend only if API key is available
const resend = process.env.RESEND_API_KEY ? new Resend(process.env.RESEND_API_KEY) : null;

interface LineItem {
  id: string;
  name: string;
  price: number;
  quantity: number;
  billingCycle: "one-time" | "monthly";
}

interface NewOrderEmailData {
  name: string;
  email: string;
  company?: string | null;
  phone?: string | null;
  projectDetails: string;
  orderId: string;
  price: number;
  currency: string;
  lineItems?: LineItem[];
}

export async function sendNewOrderNotification(data: NewOrderEmailData): Promise<boolean> {
  if (!resend) {
    console.warn("Resend API key not configured. Email notification skipped.");
    return false;
  }

  const fromEmail = process.env.RESEND_FROM_EMAIL || "orders@lenquant.com";
  const teamEmails = [
    "fern2gue@gmail.com",
    "fernando@lenquant.com",
    "pedro@lenquant.com",
    "pedrocdiegues@gmail.com"
  ];
  const appUrl = process.env.NEXT_PUBLIC_APP_URL || "https://sites.lenquant.com";

  // Build line items HTML
  let lineItemsHtml = "";
  let hasMonthlyServices = false;

  if (data.lineItems && data.lineItems.length > 0) {
    lineItemsHtml = data.lineItems.map((item) => {
      if (item.billingCycle === "monthly") hasMonthlyServices = true;
      const itemTotal = item.price * item.quantity;
      return `
        <tr>
          <td style="padding: 12px 0; color: #1E293B; border-bottom: 1px solid #E2E8F0;">
            ${item.quantity > 1 ? `${item.quantity}x ` : ""}${item.name}
            <span style="display: inline-block; background: ${item.billingCycle === "monthly" ? "#DBEAFE" : "#D1FAE5"}; color: ${item.billingCycle === "monthly" ? "#1E40AF" : "#065F46"}; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; margin-left: 8px;">
              ${item.billingCycle === "monthly" ? "MONTHLY" : "ONE-TIME"}
            </span>
          </td>
          <td style="padding: 12px 0; color: #1E293B; text-align: right; border-bottom: 1px solid #E2E8F0; font-weight: 600;">
            $${itemTotal.toLocaleString()}
          </td>
        </tr>
      `;
    }).join("");
  }

  try {
    // Send notification to all team members
    await resend.emails.send({
      from: fromEmail,
      to: teamEmails,
      subject: `🎉 Lenquant - NEW PAID ORDER - $${data.price.toLocaleString()} - ${data.name}`,
      html: `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>New Order</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">

  <div style="background: linear-gradient(135deg, #16A34A 0%, #15803D 100%); padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px;">
    <h1 style="color: #FFF; margin: 0; font-size: 28px;">💰 NEW PAID ORDER!</h1>
    <p style="color: #D1FAE5; margin: 10px 0 0 0; font-size: 18px; font-weight: 600;">Payment confirmed: $${data.price.toLocaleString()} ${data.currency}</p>
  </div>

  <div style="background: #FEF3C7; border: 2px solid #F59E0B; border-radius: 12px; padding: 20px; margin-bottom: 24px; text-align: center;">
    <p style="color: #92400E; margin: 0; font-size: 15px; font-weight: 600;">
      ⚡ ACTION REQUIRED: Contact customer within 4 hours (business hours)
    </p>
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
    </table>
  </div>

  ${lineItemsHtml ? `
  <div style="background: #FFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
    <h2 style="color: #1E293B; margin: 0 0 16px 0; font-size: 20px; border-bottom: 2px solid #EAB308; padding-bottom: 8px;">Order Details</h2>

    <table style="width: 100%; border-collapse: collapse;">
      ${lineItemsHtml}
      <tr>
        <td style="padding: 16px 0 0 0; color: #1E293B; font-size: 18px; font-weight: bold;">Total</td>
        <td style="padding: 16px 0 0 0; color: #16A34A; text-align: right; font-size: 20px; font-weight: bold;">$${data.price.toLocaleString()}</td>
      </tr>
    </table>

    ${hasMonthlyServices ? `
    <div style="background: #DBEAFE; border-left: 4px solid #3B82F6; padding: 12px 16px; margin-top: 16px; border-radius: 4px;">
      <p style="margin: 0; color: #1E40AF; font-size: 13px;">
        <strong>💳 Note:</strong> This order includes monthly recurring services. Customer will be billed automatically each month.
      </p>
    </div>
    ` : ""}
  </div>
  ` : ""}

  <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
    <h2 style="color: #92400E; margin: 0 0 12px 0; font-size: 18px;">📋 Project Details</h2>
    <p style="color: #78350F; margin: 0; white-space: pre-wrap; line-height: 1.6;">${data.projectDetails}</p>
  </div>

  <div style="background: #F1F5F9; border-radius: 12px; padding: 20px; margin-bottom: 24px; text-align: center;">
    <p style="margin: 0 0 16px 0; color: #475569;">View and manage this order in your admin panel:</p>
    <a href="${appUrl}/app/orders"
       style="display: inline-block; background: #EAB308; color: #1E293B; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">
      View Order Details
    </a>
  </div>

  <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
    <h3 style="color: #166534; margin: 0 0 12px 0; font-size: 16px;">📋 Next Steps:</h3>
    <ol style="margin: 0; padding-left: 20px; color: #15803D; line-height: 1.8;">
      <li>Check if customer booked kickoff call via Calendly</li>
      <li>If not booked within 4 hours → reach out manually (email/phone)</li>
      <li>Conduct 30-minute kickoff call to discuss project details</li>
      <li>Start building website immediately after kickoff call</li>
      <li>Deliver completed website within 3 days</li>
    </ol>
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
    <p style="color: #94A3B8; font-size: 14px; margin: 16px 0 0 0;">
      <a href="${appUrl}/app/orders" style="background: #EAB308; color: #1E293B; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block;">View Order Details</a>
    </p>
  </div>

  <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid #E2E8F0; text-align: center;">
    <p style="color: #64748B; font-size: 13px; margin: 0;">
      <strong style="color: #1E293B;">Lenquant</strong>
    </p>
    <p style="color: #94A3B8; font-size: 12px; margin: 8px 0;">
      🌐 <a href="https://sites.lenquant.com" style="color: #94A3B8; text-decoration: none;">sites.lenquant.com</a>
    </p>
    <p style="color: #94A3B8; font-size: 12px; margin: 0;">
      Premium websites delivered in 3 days
    </p>
  </div>

</body>
</html>
      `,
    });

    console.log("Order notification email sent successfully to:", teamEmails.join(", "));
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
  price: number;
  currency: string;
  lineItems?: LineItem[];
}

export async function sendCustomerConfirmation(data: CustomerConfirmationEmailData): Promise<boolean> {
  if (!resend) {
    console.warn("Resend API key not configured. Confirmation email skipped.");
    return false;
  }

  const fromEmail = process.env.RESEND_FROM_EMAIL || "orders@lenquant.com";

  // Build line items HTML for customer
  let customerLineItemsHtml = "";
  let hasMonthlyServices = false;

  if (data.lineItems && data.lineItems.length > 0) {
    customerLineItemsHtml = data.lineItems.map((item) => {
      if (item.billingCycle === "monthly") hasMonthlyServices = true;
      const itemTotal = item.price * item.quantity;
      return `
        <tr>
          <td style="padding: 12px 0; color: #1E293B; border-bottom: 1px solid #E2E8F0;">
            ${item.quantity > 1 ? `${item.quantity}x ` : ""}${item.name}
            ${item.billingCycle === "monthly" ? `<span style="display: inline-block; background: #DBEAFE; color: #1E40AF; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; margin-left: 8px;">MONTHLY</span>` : ""}
          </td>
          <td style="padding: 12px 0; color: #1E293B; text-align: right; border-bottom: 1px solid #E2E8F0; font-weight: 600;">
            $${itemTotal.toLocaleString()}${item.billingCycle === "monthly" ? "/mo" : ""}
          </td>
        </tr>
      `;
    }).join("");
  }

  try {
    await resend.emails.send({
      from: fromEmail,
      to: data.email,
      subject: "✅ Lenquant - Payment Received - Let's Schedule Your Kickoff Call!",
      html: `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Order Confirmation</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">

  <div style="background: linear-gradient(135deg, #16A34A 0%, #15803D 100%); padding: 40px 30px; border-radius: 12px; text-align: center; margin-bottom: 30px;">
    <h1 style="color: #FFF; margin: 0; font-size: 32px;">🎉 Payment Confirmed!</h1>
    <p style="color: #D1FAE5; margin: 16px 0 0 0; font-size: 18px; line-height: 1.5;">Thank you, ${data.name}! Your order is confirmed.</p>
  </div>

  ${customerLineItemsHtml ? `
  <div style="background: #FFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
    <h2 style="color: #1E293B; margin: 0 0 16px 0; font-size: 20px; border-bottom: 2px solid #EAB308; padding-bottom: 8px;">Order Summary</h2>

    <table style="width: 100%; border-collapse: collapse;">
      ${customerLineItemsHtml}
      <tr>
        <td style="padding: 16px 0 0 0; color: #1E293B; font-size: 18px; font-weight: bold;">Total Paid</td>
        <td style="padding: 16px 0 0 0; color: #16A34A; text-align: right; font-size: 20px; font-weight: bold;">$${data.price.toLocaleString()}</td>
      </tr>
    </table>

    ${hasMonthlyServices ? `
    <div style="background: #DBEAFE; border-left: 4px solid #3B82F6; padding: 12px 16px; margin-top: 16px; border-radius: 4px;">
      <p style="margin: 0; color: #1E40AF; font-size: 13px;">
        <strong>💳 Recurring Services:</strong> Monthly services will be billed automatically each month. You can cancel anytime.
      </p>
    </div>
    ` : ""}
  </div>
  ` : ""}

  <div style="background: #FEF3C7; border: 2px solid #F59E0B; border-radius: 12px; padding: 24px; margin-bottom: 24px; text-align: center;">
    <h2 style="color: #92400E; margin: 0 0 16px 0; font-size: 22px;">📅 Next Step: Book Your Kickoff Call</h2>
    <p style="color: #78350F; margin: 0 0 20px 0; font-size: 15px; line-height: 1.6;">
      We're ready to start your project! Book a 30-minute kickoff call to discuss your vision and finalize details.
    </p>
    <a href="https://calendly.com/lenquant/sites"
       style="display: inline-block; background: #EAB308; color: #1E293B; padding: 16px 40px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
      📅 Book Your Kickoff Call
    </a>
    <p style="color: #92400E; margin: 16px 0 0 0; font-size: 13px;">
      Haven't booked yet? No problem! We'll reach out within 4 hours (business hours) to help you schedule.
    </p>
  </div>

  <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
    <h2 style="color: #1E293B; margin: 0 0 16px 0; font-size: 20px;">⏱️ Project Timeline</h2>
    <div style="margin-bottom: 16px;">
      <div style="margin-bottom: 16px;">
        <div style="display: inline-block; background: #EAB308; color: #1E293B; width: 32px; height: 32px; border-radius: 50%; text-align: center; line-height: 32px; font-weight: bold; margin-right: 12px;">1</div>
        <strong style="color: #1E293B;">Book Your Kickoff Call</strong>
        <p style="margin: 8px 0 0 44px; color: #64748B; font-size: 14px;">Choose a time that works for you (30 minutes)</p>
      </div>
      <div style="margin-bottom: 16px;">
        <div style="display: inline-block; background: #EAB308; color: #1E293B; width: 32px; height: 32px; border-radius: 50%; text-align: center; line-height: 32px; font-weight: bold; margin-right: 12px;">2</div>
        <strong style="color: #1E293B;">Kickoff Call (Within 48 Hours)</strong>
        <p style="margin: 8px 0 0 44px; color: #64748B; font-size: 14px;">We'll discuss your brand, goals, and website requirements</p>
      </div>
      <div>
        <div style="display: inline-block; background: #EAB308; color: #1E293B; width: 32px; height: 32px; border-radius: 50%; text-align: center; line-height: 32px; font-weight: bold; margin-right: 12px;">3</div>
        <strong style="color: #1E293B;">Website Delivered (3 Days)</strong>
        <p style="margin: 8px 0 0 44px; color: #64748B; font-size: 14px;">Receive your complete, production-ready website</p>
      </div>
    </div>
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
    <p style="margin: 0 0 8px 0;">
      <a href="mailto:pedro@lenquant.com" style="color: #EAB308; text-decoration: none; font-weight: 600;">📧 pedro@lenquant.com</a>
    </p>
    <p style="margin: 0;">
      <a href="tel:+18457211974" style="color: #EAB308; text-decoration: none; font-weight: 600;">📞 +1 (845) 721-1974</a>
    </p>
  </div>

  <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid #E2E8F0; text-align: center;">
    <p style="color: #64748B; font-size: 14px; margin: 0;">
      <strong style="color: #1E293B;">Lenquant</strong>
    </p>
    <p style="color: #94A3B8; font-size: 12px; margin: 8px 0;">
      🌐 <a href="https://sites.lenquant.com" style="color: #94A3B8; text-decoration: none;">sites.lenquant.com</a>
    </p>
    <p style="color: #94A3B8; font-size: 12px; margin: 0;">
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
