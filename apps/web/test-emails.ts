/**
 * Test script to send example emails for the new order notification system
 *
 * Usage: node --loader ts-node/esm test-emails.ts
 * Or: npx tsx test-emails.ts
 */

import { sendNewOrderNotification, sendCustomerConfirmation } from "./src/lib/email";

// Example order with multiple services
const exampleLineItems = [
  {
    id: "professional",
    name: "Professional Website",
    price: 1000,
    quantity: 1,
    billingCycle: "one-time" as const,
  },
  {
    id: "extra_pages",
    name: "Additional Pages",
    price: 50,
    quantity: 5,
    billingCycle: "one-time" as const,
  },
  {
    id: "maintenance",
    name: "Maintenance Service",
    price: 500,
    quantity: 1,
    billingCycle: "monthly" as const,
  },
  {
    id: "hosting",
    name: "Hosting Service",
    price: 200,
    quantity: 1,
    billingCycle: "monthly" as const,
  },
];

const totalPrice = exampleLineItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);

async function sendTestEmails() {
  console.log("🚀 Sending test emails...\n");

  // Test 1: Send team notification email
  console.log("📧 Sending team notification email to 4 team members...");
  const teamEmailSent = await sendNewOrderNotification({
    name: "John Smith",
    email: "john.smith@example.com",
    company: "Acme Corporation",
    phone: "+1 (555) 123-4567",
    projectDetails: "We need a modern, professional website for our SaaS product. Looking for a clean design with focus on conversion optimization. Target audience is B2B software buyers. We have existing branding guidelines we can share.",
    orderId: "TEST_" + Date.now(),
    price: totalPrice,
    currency: "USD",
    lineItems: exampleLineItems,
  });

  if (teamEmailSent) {
    console.log("✅ Team notification sent successfully!\n");
    console.log("   Recipients:");
    console.log("   - fern2gue@gmail.com");
    console.log("   - fernando@lenquant.com");
    console.log("   - pedro@lenquant.com");
    console.log("   - pedrocdiegues@gmail.com\n");
  } else {
    console.log("❌ Failed to send team notification\n");
  }

  // Test 2: Send customer confirmation email
  console.log("📧 Sending customer confirmation email...");
  const customerEmailSent = await sendCustomerConfirmation({
    name: "John Smith",
    email: "john.smith@example.com",
    orderId: "TEST_" + Date.now(),
    price: totalPrice,
    currency: "USD",
    lineItems: exampleLineItems,
  });

  if (customerEmailSent) {
    console.log("✅ Customer confirmation sent successfully!\n");
    console.log("   Recipient: john.smith@example.com\n");
  } else {
    console.log("❌ Failed to send customer confirmation\n");
  }

  console.log("📊 Test Summary:");
  console.log(`   Total order value: $${totalPrice.toLocaleString()}`);
  console.log(`   Line items: ${exampleLineItems.length}`);
  console.log(`   Monthly recurring: $${exampleLineItems.filter(i => i.billingCycle === "monthly").reduce((sum, i) => sum + i.price, 0)}/month`);
  console.log("\n✨ Done! Check your inboxes.");
}

// Run the test
sendTestEmails().catch((error) => {
  console.error("💥 Error sending test emails:", error);
  process.exit(1);
});
