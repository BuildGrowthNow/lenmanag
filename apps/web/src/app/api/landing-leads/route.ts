import { NextResponse } from "next/server";
import { connectToDatabase } from "@/lib/mongodb";

export async function GET() {
  try {
    const { db } = await connectToDatabase();

    // Fetch all landing page leads, sorted by most recent first
    const leads = await db
      .collection("landing_leads")
      .find({})
      .sort({ createdAt: -1 })
      .limit(100)
      .toArray();

    // Convert MongoDB ObjectId to string
    const serializedLeads = leads.map((lead) => ({
      ...lead,
      _id: lead._id.toString(),
    }));

    return NextResponse.json({
      success: true,
      leads: serializedLeads,
      count: serializedLeads.length,
    });
  } catch (error) {
    console.error("Error fetching landing leads:", error);
    return NextResponse.json(
      { error: "Failed to fetch leads" },
      { status: 500 }
    );
  }
}
