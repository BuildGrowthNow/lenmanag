import { motion } from "framer-motion";

export const metadata = {
  title: "Privacy Policy | Lenquant",
  description: "Privacy policy for Lenquant website design services",
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white py-16 px-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-12">
          <h1 className="text-5xl font-bold mb-4">Privacy Policy</h1>
          <p className="text-slate-400">Last updated: {new Date().toLocaleDateString()}</p>
        </div>

        <div className="space-y-8 text-slate-300">
          <section>
            <h2 className="text-2xl font-bold text-white mb-4">Introduction</h2>
            <p>
              Lenquant ("we," "us," "our," or "Company") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you visit our website and use our services.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">Information We Collect</h2>
            <p className="mb-4">We may collect information about you in a variety of ways. The information we may collect on the site includes:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li><strong>Personal Data:</strong> Name, email address, phone number, company name, and other contact information you provide when filling out our forms.</li>
              <li><strong>Project Information:</strong> Details about your website project, business type, and goals.</li>
              <li><strong>Usage Data:</strong> Information about how you interact with our website, including IP address, browser type, pages visited, and time spent on pages.</li>
              <li><strong>Payment Information:</strong> Credit card details are processed by our payment provider and are not stored on our servers.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">How We Use Your Information</h2>
            <p className="mb-4">We use the information we collect in the following ways:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>To deliver and improve our website design services</li>
              <li>To communicate with you about your project and orders</li>
              <li>To send promotional emails and updates (with your consent)</li>
              <li>To prevent fraud and enhance security</li>
              <li>To comply with legal obligations</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">Data Security</h2>
            <p>
              We implement appropriate technical and organizational security measures to protect your personal information against unauthorized access, disclosure, alteration, and destruction. However, no method of transmission over the internet is 100% secure.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">Third-Party Sharing</h2>
            <p className="mb-4">We do not sell your personal information. We may share your information with:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Service providers who assist us in delivering our services</li>
              <li>Payment processors for order fulfillment</li>
              <li>Legal authorities when required by law</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">Cookies and Tracking</h2>
            <p>
              We use cookies and similar tracking technologies to enhance your experience on our website. You can control cookie preferences through your browser settings.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">Your Rights</h2>
            <p className="mb-4">You have the right to:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Access your personal information</li>
              <li>Correct inaccurate data</li>
              <li>Request deletion of your data</li>
              <li>Opt-out of marketing communications</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">Contact Us</h2>
            <p>
              If you have questions about this Privacy Policy or our privacy practices, please contact us at:
            </p>
            <div className="mt-4 p-6 bg-white/5 rounded-xl border border-white/10">
              <p className="mb-2"><strong>Lenquant</strong></p>
              <p>510 South Main Street, South Bend, IN 46601</p>
              <p>Email: <a href="mailto:contact@lenquant.com" className="text-yellow-500 hover:text-yellow-400">contact@lenquant.com</a></p>
              <p>Phone: <a href="tel:+18457211974" className="text-yellow-500 hover:text-yellow-400">+1 (845) 721-1974</a></p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">Policy Changes</h2>
            <p>
              We may update this Privacy Policy from time to time. We will notify you of any changes by updating the "Last updated" date of this policy.
            </p>
          </section>
        </div>

        <div className="mt-16 p-8 bg-yellow-500/10 rounded-2xl border border-yellow-500/20">
          <p className="text-yellow-400 text-center">
            By using our website and services, you acknowledge that you have read and understood this Privacy Policy.
          </p>
        </div>
      </div>
    </div>
  );
}
