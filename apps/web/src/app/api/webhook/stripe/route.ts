import { NextRequest, NextResponse } from "next/server";
import { getStripe } from "@/lib/stripe";
import { connectToDatabase } from "@/lib/mongodb";
import { ObjectId } from "mongodb";
import { sendNewOrderNotification, sendCustomerConfirmation } from "@/lib/email";

export async function POST(request: NextRequest) {
  const body = await request.text();
  const signature = request.headers.get("stripe-signature");

  if (!signature) {
    return NextResponse.json({ error: "Missing signature" }, { status: 400 });
  }

  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!webhookSecret) {
    console.error("STRIPE_WEBHOOK_SECRET is not set");
    return NextResponse.json({ error: "Webhook not configured" }, { status: 500 });
  }

  let event;
  try {
    const stripe = getStripe();
    event = stripe.webhooks.constructEvent(body, signature, webhookSecret);
  } catch (err) {
    console.error("Webhook signature verification failed:", err);
    return NextResponse.json({ error: "Invalid signature" }, { status: 400 });
  }

  if (event.type === "checkout.session.completed") {
    const session = event.data.object;
    const leadId = session.metadata?.leadId;

    if (leadId) {
      try {
        const { db } = await connectToDatabase();

        await db.collection("landing_leads").updateOne(
          { _id: new ObjectId(leadId) },
          {
            $set: {
              paymentStatus: "paid",
              status: "confirmed",
              stripeSessionId: session.id,
              stripePaymentIntentId: session.payment_intent,
              paidAt: new Date(),
              updatedAt: new Date(),
            },
          }
        );

        // Fetch lead data for email
        const lead = await db.collection("landing_leads").findOne({ _id: new ObjectId(leadId) });

        if (lead) {
          Promise.all([
            sendNewOrderNotification({
              name: lead.name,
              email: lead.email,
              company: lead.company,
              phone: lead.phone,
              projectDetails: lead.projectDetails,
              orderId: leadId,
              price: lead.price,
              currency: lead.currency,
            }),
            sendCustomerConfirmation({
              name: lead.name,
              email: lead.email,
              orderId: leadId,
            }),
          ]).catch((error) => {
            console.error("Error sending email notifications:", error);
          });
        }

        console.log(`Payment confirmed for lead ${leadId}`);
      } catch (error) {
        console.error("Error updating lead payment status:", error);
      }
    }
  }

  return NextResponse.json({ received: true });
}
