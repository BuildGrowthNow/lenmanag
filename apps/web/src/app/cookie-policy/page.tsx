export const metadata = {
  title: "Cookie Policy | Lenquant",
  description: "Cookie policy for Lenquant website design services",
};

export default function CookiePolicyPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white py-16 px-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-12">
          <h1 className="text-5xl font-bold mb-4">Cookie Policy</h1>
          <p className="text-slate-400">Last updated: {new Date().toLocaleDateString()}</p>
        </div>

        <div className="space-y-8 text-slate-300">
          <section>
            <h2 className="text-2xl font-bold text-white mb-4">What Are Cookies?</h2>
            <p>
              Cookies are small files that are stored on your device when you visit our website. They contain information that allows us to recognize your device and remember your preferences when you return to our site.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">Types of Cookies We Use</h2>
            <p className="mb-4">We use the following types of cookies:</p>
            <ul className="list-disc list-inside space-y-3 ml-4">
              <li>
                <strong>Essential Cookies:</strong> These cookies are necessary for the website to function properly. They enable basic functionality and security features.
              </li>
              <li>
                <strong>Performance Cookies:</strong> These cookies help us understand how visitors use our website by collecting anonymous data. This helps us improve our services.
              </li>
              <li>
                <strong>Functional Cookies:</strong> These cookies remember your preferences and settings to provide a better browsing experience.
              </li>
              <li>
                <strong>Marketing Cookies:</strong> These cookies track your activity to show you relevant content and advertisements.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">Third-Party Cookies</h2>
            <p>
              We use cookies from third-party service providers including Google Analytics for tracking website usage and behavior. These third parties may use the information collected for their own purposes in accordance with their privacy policies.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">How Long Do Cookies Last?</h2>
            <p className="mb-4">
              Cookies have different lifespans:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li><strong>Session cookies:</strong> Deleted when you close your browser</li>
              <li><strong>Persistent cookies:</strong> Remain on your device for a specified period or until manually deleted</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">Managing Cookies</h2>
            <p className="mb-4">
              You have the right to accept or reject cookies. Most browsers allow you to:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>View what cookies are on your device and delete them individually</li>
              <li>Block all cookies or specific types of cookies</li>
              <li>Set preferences for cookie acceptance</li>
              <li>Clear all cookies when you close your browser</li>
            </ul>
            <p className="mt-4">
              Please note that disabling certain cookies may affect the functionality of our website.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">Your Privacy Rights</h2>
            <p>
              We are committed to protecting your privacy. Cookies are used in accordance with our Privacy Policy. For more information about how we handle your data, please review our Privacy Policy.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">Contact Us</h2>
            <p>
              If you have questions about our use of cookies, please contact us:
            </p>
            <div className="mt-4 p-6 bg-white/5 rounded-xl border border-white/10">
              <p className="mb-2"><strong>Lenquant</strong></p>
              <p>510 South Main Street, South Bend, IN 46601</p>
              <p>Email: <a href="mailto:contact@lenquant.com" className="text-yellow-500 hover:text-yellow-400">contact@lenquant.com</a></p>
              <p>Phone: <a href="tel:+18457211974" className="text-yellow-500 hover:text-yellow-400">+1 (845) 721-1974</a></p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-white mb-4">Changes to This Policy</h2>
            <p>
              We may update this Cookie Policy from time to time. We will notify you of any material changes by updating the &quot;Last updated&quot; date of this policy.
            </p>
          </section>
        </div>

        <div className="mt-16 p-8 bg-yellow-500/10 rounded-2xl border border-yellow-500/20">
          <p className="text-yellow-400 text-center">
            By continuing to use our website, you consent to our use of cookies as described in this policy.
          </p>
        </div>
      </div>
    </div>
  );
}
