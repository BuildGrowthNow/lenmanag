import { NextRequest, NextResponse } from "next/server";
import { connectToDatabase } from "@/lib/mongodb";
import { sendNewOrderNotification, sendCustomerConfirmation } from "@/lib/email";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate required fields
    if (!body.name || !body.email || !body.projectDetails) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 }
      );
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(body.email)) {
      return NextResponse.json(
        { error: "Invalid email address" },
        { status: 400 }
      );
    }

    // Save to MongoDB
    const { db } = await connectToDatabase();
    const lead = {
      name: body.name,
      email: body.email,
      company: body.company || null,
      phone: body.phone || null,
      projectDetails: body.projectDetails,
      source: "landing_page",
      status: "pending",
      paymentStatus: "unpaid",
      orderType: "website_generation",
      price: 1000,
      currency: "USD",
      createdAt: new Date(),
      updatedAt: new Date(),
      metadata: {
        userAgent: request.headers.get("user-agent") || null,
        referrer: request.headers.get("referer") || null,
        ipAddress: request.headers.get("x-forwarded-for") || request.headers.get("x-real-ip") || null,
      },
    };

    const result = await db.collection("landing_leads").insertOne(lead);

    // Log successful submission
    console.log("New landing page lead:", {
      id: result.insertedId,
      name: body.name,
      email: body.email,
      company: body.company,
      timestamp: new Date().toISOString(),
    });

    // Send email notifications (non-blocking)
    Promise.all([
      sendNewOrderNotification({
        name: body.name,
        email: body.email,
        company: body.company,
        phone: body.phone,
        projectDetails: body.projectDetails,
        orderId: result.insertedId.toString(),
        price: lead.price,
        currency: lead.currency,
      }),
      sendCustomerConfirmation({
        name: body.name,
        email: body.email,
        orderId: result.insertedId.toString(),
        price: lead.price,
        currency: lead.currency,
      }),
    ]).catch((error) => {
      console.error("Error sending email notifications:", error);
      // Don't fail the request if emails fail
    });

    return NextResponse.json({
      success: true,
      message: "Lead submitted successfully",
      id: result.insertedId.toString(),
    });
  } catch (error) {
    console.error("Error submitting lead:", error);
    return NextResponse.json(
      { error: "Failed to submit form. Please try again." },
      { status: 500 }
    );
  }
}
