import { NextRequest, NextResponse } from "next/server";
import { getStripe } from "@/lib/stripe";
import { connectToDatabase } from "@/lib/mongodb";
import { ADD_ONS, BASE_PRICE, calculateTotal, type SelectedAddOns } from "@/lib/pricing";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, email, company, phone, projectDetails, addOns } = body;

    if (!name || !email || !projectDetails) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 }
      );
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return NextResponse.json(
        { error: "Invalid email address" },
        { status: 400 }
      );
    }

    const selectedAddOns: SelectedAddOns = addOns || {};
    const totalPrice = calculateTotal(selectedAddOns);

    // Save lead to MongoDB first
    const { db } = await connectToDatabase();
    const lead = {
      name,
      email,
      company: company || null,
      phone: phone || null,
      projectDetails,
      source: "landing_page",
      status: "pending",
      paymentStatus: "unpaid",
      orderType: "website_generation",
      price: totalPrice,
      currency: "USD",
      addOns: selectedAddOns,
      createdAt: new Date(),
      updatedAt: new Date(),
      metadata: {
        userAgent: request.headers.get("user-agent") || null,
        referrer: request.headers.get("referer") || null,
        ipAddress:
          request.headers.get("x-forwarded-for") ||
          request.headers.get("x-real-ip") ||
          null,
      },
    };

    const result = await db.collection("landing_leads").insertOne(lead);
    const leadId = result.insertedId.toString();

    // Build Stripe line items
    const lineItems: { price_data: { currency: string; product_data: { name: string; description?: string }; unit_amount: number }; quantity: number }[] = [
      {
        price_data: {
          currency: "usd",
          product_data: {
            name: "Professional Website — Landing Page",
            description: "Custom design, responsive, SEO-optimized, delivered in 3 days",
          },
          unit_amount: BASE_PRICE * 100,
        },
        quantity: 1,
      },
    ];

    for (const addon of ADD_ONS) {
      const qty = selectedAddOns[addon.id] || 0;
      if (qty > 0) {
        lineItems.push({
          price_data: {
            currency: "usd",
            product_data: {
              name: addon.name,
              description: addon.description,
            },
            unit_amount: addon.price * 100,
          },
          quantity: qty,
        });
      }
    }

    // Create Stripe Checkout Session
    const stripe = getStripe();
    const appUrl = process.env.NEXT_PUBLIC_APP_URL || "https://sites.lenquant.com";

    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      customer_email: email,
      line_items: lineItems,
      metadata: {
        leadId,
        customerName: name,
        company: company || "",
      },
      success_url: `${appUrl}/landing?success=true&session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${appUrl}/landing?canceled=true`,
    });

    return NextResponse.json({
      success: true,
      checkoutUrl: session.url,
      leadId,
    });
  } catch (error) {
    console.error("Error creating checkout session:", error);
    return NextResponse.json(
      { error: "Failed to create checkout session. Please try again." },
      { status: 500 }
    );
  }
}
