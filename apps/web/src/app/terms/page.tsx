export const metadata = {
  title: "Terms of Service | Lenquant",
  description: "Terms of service for Lenquant website design services",
};

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white py-16 px-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-12">
          <h1 className="text-5xl font-bold mb-4">Terms of Service</h1>
          <p className="text-slate-400">Last updated: {new Date().toLocaleDateString()}</p>
        </div>

        <div className="space-y-8 text-slate-300">
          <section>
            <h2 className="text-2xl font-bold text-white mb-4">1. Agreement to Terms</h2>
            <p>
              By accessing and using Lenquant's website and services, you accept and agree to be bound by the terms and provision of this agreement. If you do not agree to abide by the above, please do not use this service.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">2. Service Description</h2>
            <p className="mb-4">
              Lenquant provides professional website design and development services. Our service includes:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Custom website design and development</li>
              <li>Mobile-responsive design</li>
              <li>Basic SEO optimization</li>
              <li>Initial hosting setup (first year included)</li>
              <li>Free minor updates for 30 days after delivery</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">3. Pricing and Payment</h2>
            <p className="mb-4">
              All prices are in USD and are subject to change without notice. Prices quoted are one-time fees unless otherwise specified. Payment must be made before service commencement. We accept major credit cards processed through our secure payment partner.
            </p>
            <p>
              Add-on services and recurring services will be billed as specified at the time of purchase.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">4. Delivery Timeline</h2>
            <p>
              We guarantee delivery of your website within the specified timeline (standard: 3 days, priority: 1 day). Delivery is contingent upon receiving all necessary information and content from you in a timely manner. Delays caused by client-provided content or feedback may extend the timeline.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">5. Client Responsibilities</h2>
            <p className="mb-4">
              As a client, you agree to:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Provide accurate, non-infringing content and materials</li>
              <li>Respond promptly to requests for feedback and information</li>
              <li>Ensure you have rights to all content provided</li>
              <li>Comply with all applicable laws and regulations</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">6. Intellectual Property</h2>
            <p className="mb-4">
              Upon full payment, you own all rights to the website design and code created for you. You may not resell, redistribute, or use the design for unauthorized purposes. Custom code and design are created specifically for your use.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">7. Satisfaction Guarantee</h2>
            <p>
              We stand behind our work with a 100% satisfaction guarantee. If you are not satisfied with the delivered website within 7 days of delivery, we will provide a full refund. This guarantee applies only to the base service and does not cover add-on services or additional features unless specifically requested.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">8. Limitation of Liability</h2>
            <p>
              In no event shall Lenquant be liable for any indirect, incidental, special, consequential, or punitive damages resulting from your use or inability to use the services, even if we have been advised of the possibility of such damages.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">9. Hosting and Maintenance</h2>
            <p className="mb-4">
              First-year hosting is included with all website packages. After the first year, you may continue hosting with us or transfer your domain. For ongoing maintenance and support, separate service agreements apply.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">10. Third-Party Content</h2>
            <p>
              Your website may include links to third-party websites. Lenquant is not responsible for the content, accuracy, or practices of these external sites. Your use of third-party services is subject to their terms of service.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">11. Confidentiality</h2>
            <p>
              We respect the confidentiality of your business information and will not disclose it to third parties without your written consent, except as required by law.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">12. Termination</h2>
            <p>
              Either party may terminate service agreements with written notice. Upon termination, you retain ownership of your website and data. Refunds are subject to our refund policy as stated in the satisfaction guarantee section.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">13. Modifications to Terms</h2>
            <p>
              Lenquant reserves the right to modify these terms at any time. Changes will be effective upon posting to the website. Your continued use of our services constitutes acceptance of modified terms.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">14. Governing Law</h2>
            <p>
              These terms are governed by and construed in accordance with the laws of Indiana, and you irrevocably submit to the exclusive jurisdiction of the courts in that location.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">15. Contact Information</h2>
            <p>
              For questions about these Terms of Service, please contact us at:
            </p>
            <div className="mt-4 p-6 bg-white/5 rounded-xl border border-white/10">
              <p className="mb-2"><strong>Lenquant</strong></p>
              <p>510 South Main Street, South Bend, IN 46601</p>
              <p>Email: <a href="mailto:contact@lenquant.com" className="text-yellow-500 hover:text-yellow-400">contact@lenquant.com</a></p>
              <p>Phone: <a href="tel:+18457211974" className="text-yellow-500 hover:text-yellow-400">+1 (845) 721-1974</a></p>
            </div>
          </section>
        </div>

        <div className="mt-16 p-8 bg-yellow-500/10 rounded-2xl border border-yellow-500/20">
          <p className="text-yellow-400 text-center">
            By using our services, you acknowledge that you have read and agreed to these Terms of Service.
          </p>
        </div>
      </div>
    </div>
  );
}
