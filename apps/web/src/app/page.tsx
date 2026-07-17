"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useSupportsHover } from "@/hooks/use-supports-hover";
import {
  CheckCircle2,
  ArrowRight,
  Clock,
  Palette,
  Code,
  Rocket,
  Users,
  PartyPopper,
  Shield,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Navbar } from "@/components/landing/navbar";
import { SocialProofTicker } from "@/components/landing/social-proof-ticker";
import { AnimatedHeroHeadline } from "@/components/landing/animated-hero-headline";
import { SocialProofNotifications } from "@/components/landing/social-proof-notifications";
import { AnimatedStats } from "@/components/landing/animated-stats";
import { TrustedCompanies } from "@/components/landing/trusted-companies";
import { FeaturesSolarSystem } from "@/components/landing/features-solar-system";
import { CaseStudiesCarousel } from "@/components/landing/case-studies-carousel";
import { WorkShowcase } from "@/components/landing/work-showcase";
import { HeroSiteColumns } from "@/components/landing/hero-site-columns";
import { SocialWall } from "@/components/landing/social-wall";
import { FAQSection } from "@/components/landing/faq-section";
import { PricingConfigurator } from "@/components/landing/pricing-configurator";
import { RiskReversalBadge } from "@/components/landing/risk-reversal-badge";
import { Footer } from "@/components/landing/footer";
import { type SelectedAddOns } from "@/lib/pricing";

export default function SitesLandingPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    company: "",
    phone: "",
    projectDetails: "",
  });
  const [selectedAddOns, setSelectedAddOns] = useState<SelectedAddOns>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [step, setStep] = useState<"configure" | "details">("configure");
  const supportsHover = useSupportsHover();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("success") === "true") {
      setShowSuccess(true);
    }
  }, []);

  const handleCheckout = (addOns: SelectedAddOns) => {
    setSelectedAddOns(addOns);
    setStep("details");
    setTimeout(() => {
      document.getElementById("order-form")?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const response = await fetch("/api/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...formData,
          addOns: selectedAddOns,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to create checkout");
      }

      if (data.checkoutUrl) {
        window.location.href = data.checkoutUrl;
      }
    } catch (error) {
      console.error("Error creating checkout:", error);
      setSubmitError(
        error instanceof Error
          ? error.message
          : "Failed to process. Please try again."
      );
      setIsSubmitting(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  if (showSuccess) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white flex items-center justify-center px-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center max-w-lg"
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring" }}
            className="w-20 h-20 mx-auto mb-8 rounded-full bg-green-500/20 flex items-center justify-center"
          >
            <PartyPopper className="w-10 h-10 text-green-400" />
          </motion.div>
          <h1 className="text-4xl font-bold mb-4">Payment Confirmed!</h1>
            <p className="text-xl text-slate-300 mb-6">
              Thank you for your order. We&apos;ve started working on your website.
            </p>
          <div className="p-6 rounded-2xl bg-white/5 border border-white/10 text-left space-y-3 mb-8">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0" />
              <span className="text-slate-300">Payment received successfully</span>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0" />
              <span className="text-slate-300">Confirmation email sent</span>
            </div>
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-yellow-500 flex-shrink-0" />
              <span className="text-slate-300">Your website will be ready within 3 days</span>
            </div>
          </div>
          <p className="text-sm text-slate-400">
            Questions? Contact us at{" "}
            <a href="mailto:fern2gue@gmail.com" className="text-yellow-500 hover:underline">
              fern2gue@gmail.com
            </a>
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <>
      {/* Structured Data for SEO */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Service",
            name: "Professional Website Design & Development",
            provider: {
              "@type": "Organization",
              name: "Lenquant",
              url: "https://sites.lenquant.com",
            },
            description:
              "Professional websites delivered in 3 days. Custom design, premium technology, SEO optimization included.",
            offers: {
              "@type": "Offer",
              price: "1000",
              priceCurrency: "USD",
              availability: "https://schema.org/InStock",
            },
            areaServed: {
              "@type": "Place",
              name: "Worldwide",
            },
          }),
        }}
      />

      {/* Conversion Features */}
      <SocialProofTicker />
      <RiskReversalBadge />

      {/* Navigation */}
      <Navbar />

      {/* Hero Background - Site columns behind everything */}
      <HeroSiteColumns />

      {/* Social Proof Notifications */}
      <SocialProofNotifications />

      <div className="min-h-screen bg-gradient-to-br from-zinc-950 via-zinc-900 to-zinc-950 text-white overflow-hidden">
        {/* Animated Background - Optimized for performance */}
        <div className="fixed inset-0 opacity-30 pointer-events-none hidden lg:block will-change-transform">
          <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]" />
          <motion.div
            className="absolute top-0 -left-4 w-96 h-96 bg-yellow-500/30 rounded-full mix-blend-multiply filter blur-3xl will-change-transform"
            animate={{
              x: [0, 150, -100, 50, 0],
              y: [0, 80, -60, 40, 0],
            }}
            transition={{
              duration: 25,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
          <motion.div
            className="absolute top-0 right-4 w-96 h-96 bg-purple-500/20 rounded-full mix-blend-multiply filter blur-3xl will-change-transform"
            animate={{
              x: [0, -150, 100, -50, 0],
              y: [0, 100, -80, 50, 0],
            }}
            transition={{
              duration: 30,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
          <motion.div
            className="absolute bottom-0 left-1/2 w-80 h-80 bg-cyan-500/10 rounded-full mix-blend-multiply filter blur-3xl will-change-transform"
            animate={{
              x: [0, 80, -100, 40, 0],
              y: [0, -60, 80, -40, 0],
            }}
            transition={{
              duration: 28,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        </div>

        {/* Hero Section */}
        <section className="relative px-6 pt-20 pb-32">
          <div className="max-w-7xl mx-auto relative">
            {/* Money-Back Guarantee Badge */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="flex justify-center mb-6"
            >
              <motion.div
                animate={{
                  boxShadow: [
                    "0 0 20px rgba(34, 197, 94, 0.3)",
                    "0 0 40px rgba(34, 197, 94, 0.5)",
                    "0 0 20px rgba(34, 197, 94, 0.3)",
                  ],
                }}
                transition={{ duration: 2, repeat: Infinity }}
                className="px-5 py-2.5 rounded-full bg-green-500/10 border border-green-500/50 backdrop-blur-sm flex items-center gap-2"
              >
                <Shield className="w-4 h-4 text-green-400" />
                <span className="text-sm font-bold text-green-400">
                  100% Money-Back Guarantee
                </span>
              </motion.div>
            </motion.div>

            <div className="mb-12">
              <AnimatedHeroHeadline />
            </div>

            <motion.div
              className="flex justify-center"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8, duration: 0.5 }}
            >
              <motion.div
                {...(supportsHover && { whileHover: { scale: 1.05 } })}
                whileTap={{ scale: 0.95 }}
                className="inline-block"
              >
                <Button
                  onClick={() =>
                    document
                      .getElementById("pricing")
                      ?.scrollIntoView({ behavior: "smooth" })
                  }
                  className="px-8 py-6 text-lg font-semibold bg-yellow-500 hover:bg-yellow-600 text-slate-900 rounded-full shadow-2xl shadow-yellow-500/50 transition-all"
                >
                  Start Your Masterpiece
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </motion.div>
            </motion.div>

            {/* Stats */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.8 }}
              className="mt-24"
            >
              <AnimatedStats />
            </motion.div>
          </div>
        </section>

        {/* Logo Wall - Trusted Companies */}
        <section id="trusted">
          <TrustedCompanies />
        </section>

        {/* Features Section - Solar System */}
        <section id="features">
          <FeaturesSolarSystem />
        </section>

        {/* How It Works */}
        <section id="process" className="relative px-6 py-24">
          <div className="max-w-7xl mx-auto">
            <motion.div
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
              className="text-center mb-16"
            >
              <h2 className="text-5xl font-bold mb-4">
                Our <span className="text-yellow-500">4-Phase Process</span>
              </h2>
              <p className="text-xl text-slate-400">
                From order to launch in four clear phases over 3 days
              </p>
            </motion.div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 relative">
              {[
                {
                  step: "01",
                  title: "Discovery",
                  description:
                    "Fill out our form and share your vision. We'll align on your brand, goals, target audience, and key requirements.",
                  icon: Users,
                },
                {
                  step: "02",
                  title: "Design",
                  description:
                    "Our designers create a custom, on-brand layout. We craft the visual identity and user experience for your site.",
                  icon: Palette,
                },
                {
                  step: "03",
                  title: "Development",
                  description:
                    "Our platform generates your website with premium tech. Fully responsive, SEO-optimized, and performance-tuned.",
                  icon: Code,
                },
                {
                  step: "04",
                  title: "Delivery",
                  description:
                    "Receive your complete website in 3 days. Review, approve, and go live immediately with everything included.",
                  icon: Rocket,
                },
              ].map((process, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.15, duration: 0.5 }}
                  viewport={{ once: true, amount: 0.3 }}
                  className="relative"
                >
                  <motion.div {...(supportsHover && { whileHover: { scale: 1.05 } })} className="text-center">
                    <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-yellow-500 to-yellow-600 flex items-center justify-center text-2xl font-bold shadow-2xl shadow-yellow-500/50 relative z-10">
                      {process.step}
                    </div>
                    <div className="mb-4 flex justify-center">
                      <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center border border-white/10">
                        <process.icon className="w-6 h-6 text-yellow-500" />
                      </div>
                    </div>
                    <h3 className="text-xl font-bold mb-3 text-white">{process.title}</h3>
                    <p className="text-slate-400 leading-relaxed text-sm">
                      {process.description}
                    </p>
                  </motion.div>
                </motion.div>
              ))}
            </div>

            {/* Timeline Line - Below Icons */}
            <motion.div
              initial={{ opacity: 0, scaleX: 0 }}
              whileInView={{ opacity: 1, scaleX: 1 }}
              transition={{ delay: 0.4, duration: 0.8 }}
              viewport={{ once: true }}
              className="hidden lg:flex justify-center mt-12 origin-left"
            >
              <div className="h-0.5 w-3/4 bg-gradient-to-r from-transparent via-yellow-500/50 to-transparent" />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.5 }}
              viewport={{ once: true }}
              className="mt-16 text-center"
            >
              <div className="inline-flex items-center gap-4 px-6 py-4 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl">
                <Clock className="w-6 h-6 text-yellow-500" />
                <div className="text-left">
                  <div className="text-sm text-slate-400">Total Timeline</div>
                  <div className="text-2xl font-bold text-white">
                    3 Days <span className="text-yellow-500">Guaranteed</span>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        {/* What You Get */}
        <section id="included" className="relative px-6 py-24 bg-slate-900/50">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
              className="text-center mb-16"
            >
              <h2 className="text-5xl font-bold mb-4">
                Everything <span className="text-yellow-500">Included</span>
              </h2>
              <p className="text-xl text-slate-400">
                In the base package. One price. Everything you need.
              </p>
            </motion.div>

            <div className="grid md:grid-cols-2 gap-4">
              {[
                "Professional custom design built for your brand",
                "Works perfectly on phones and tablets",
                "Loads instantly so customers don't wait",
                "Found easily on Google search",
                "Secure and trusted by visitors",
                "Connect with your customers easily",
                "Share your success on social media",
                "Full ownership of all code and assets",
                "Delivered ready to deploy anywhere",
                "Free minor revisions for 7 days after launch",
              ].map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05, duration: 0.3 }}
                  viewport={{ once: true, amount: 0.3 }}
                  {...(supportsHover && { whileHover: { x: 10 } })}
                  className="flex items-center gap-3 p-4 rounded-xl bg-white/5 md:backdrop-blur-sm border border-white/10 [@media(hover:hover)]:hover:border-yellow-500/50 md:transition-all"
                >
                  <CheckCircle2 className="w-6 h-6 text-yellow-500 flex-shrink-0" />
                  <span className="text-lg text-white">{item}</span>
                </motion.div>
              ))}
            </div>

            {/* CTA Button */}
            <motion.div
              className="flex justify-center mt-12"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              viewport={{ once: true }}
            >
              <motion.div
                {...(supportsHover && { whileHover: { scale: 1.05 } })}
                whileTap={{ scale: 0.95 }}
              >
                <Button
                  onClick={() =>
                    document
                      .getElementById("pricing")
                      ?.scrollIntoView({ behavior: "smooth" })
                  }
                  className="px-8 py-6 text-lg font-semibold bg-yellow-500 hover:bg-yellow-600 text-zinc-900 rounded-full shadow-2xl shadow-yellow-500/50 transition-all"
                >
                  Start Your Masterpiece
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* Work Showcase - Real Sites */}
        <WorkShowcase />

        {/* Case Studies Section */}
        <CaseStudiesCarousel />

        {/* Social Wall - Real Customers */}
        <section id="testimonials">
          <SocialWall />

          {/* CTA After Social Wall */}
          <motion.div
            className="flex justify-center mt-12 px-6"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
          >
            <motion.div
              {...(supportsHover && { whileHover: { scale: 1.05 } })}
              whileTap={{ scale: 0.95 }}
            >
              <Button
                onClick={() =>
                  document
                    .getElementById("pricing")
                    ?.scrollIntoView({ behavior: "smooth" })
                }
                className="px-8 py-6 text-lg font-semibold bg-yellow-500 hover:bg-yellow-600 text-zinc-900 rounded-full shadow-2xl shadow-yellow-500/50 transition-all"
              >
                Create Your Masterpiece Now
                <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
            </motion.div>
          </motion.div>
        </section>

        {/* Pricing Configurator */}
        <section id="pricing" className="relative px-6 py-24">
          <div className="max-w-6xl mx-auto">
            {step === "configure" && (
              <PricingConfigurator onCheckout={handleCheckout} isLoading={isSubmitting} />
            )}

            {step === "details" && (
              <motion.div
                id="order-form"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="max-w-xl mx-auto"
              >
                <button
                  onClick={() => setStep("configure")}
                  className="mb-6 text-sm text-slate-400 hover:text-white transition-colors flex items-center gap-2"
                >
                  <ArrowRight className="w-4 h-4 rotate-180" />
                  Back to package selection
                </button>

                <h3 className="text-3xl font-bold mb-2 text-white">
                  Almost there!
                </h3>
                <p className="text-slate-400 mb-8">
                  Tell us about your project and we&apos;ll redirect you to secure payment.
                </p>

                <form onSubmit={handleSubmit} className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium mb-2 text-white">
                      Full Name *
                    </label>
                    <Input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      required
                      placeholder="John Doe"
                      className="bg-white/5 border-white/10 text-white placeholder:text-slate-500 focus:border-yellow-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2 text-white">
                      Email *
                    </label>
                    <Input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      required
                      placeholder="john@company.com"
                      className="bg-white/5 border-white/10 text-white placeholder:text-slate-500 focus:border-yellow-500"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-2 text-white">
                        Company
                      </label>
                      <Input
                        type="text"
                        name="company"
                        value={formData.company}
                        onChange={handleChange}
                        placeholder="Your Company"
                        className="bg-white/5 border-white/10 text-white placeholder:text-slate-500 focus:border-yellow-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2 text-white">
                        Phone
                      </label>
                      <Input
                        type="tel"
                        name="phone"
                        value={formData.phone}
                        onChange={handleChange}
                        placeholder="+1 (555) 000-0000"
                        className="bg-white/5 border-white/10 text-white placeholder:text-slate-500 focus:border-yellow-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2 text-white">
                      Project Details *
                    </label>
                    <Textarea
                      name="projectDetails"
                      value={formData.projectDetails}
                      onChange={handleChange}
                      required
                      placeholder="Tell us about your project, goals, and any specific requirements..."
                      rows={4}
                      className="bg-white/5 border-white/10 text-white placeholder:text-slate-500 focus:border-yellow-500 resize-none"
                    />
                  </div>

                  {submitError && (
                    <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-xl">
                      <p className="text-sm text-red-400 text-center">{submitError}</p>
                    </div>
                  )}

                  <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                    <Button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full py-6 text-lg font-bold bg-yellow-500 hover:bg-yellow-600 text-slate-900 rounded-xl shadow-2xl shadow-yellow-500/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSubmitting ? "Redirecting to payment..." : "Continue to Payment"}
                      <ArrowRight className="ml-2 w-5 h-5" />
                    </Button>
                  </motion.div>

                  <p className="text-xs text-center text-slate-500">
                    Secure payment via Stripe. Money-back guarantee.
                  </p>
                </form>
              </motion.div>
            )}
          </div>
        </section>

        {/* FAQ Section */}
        <section id="faq">
          <FAQSection />
        </section>

        {/* Final CTA */}
        <section className="relative px-6 py-24 bg-gradient-to-br from-yellow-500/10 via-transparent to-purple-500/10">
          <div className="max-w-4xl mx-auto text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
            >
              <h2 className="text-5xl md:text-6xl font-bold mb-6 text-white">
                Your Masterpiece Awaits
                <br />
                <span className="text-yellow-500">Premium Design • $1,000<br />• 3 Days delivery</span>
              </h2>
              <p className="text-xl text-slate-300 mb-10">
                Join hundreds of business owners who trusted us to create their breakthrough website
              </p>
              <motion.div {...(supportsHover && { whileHover: { scale: 1.05 } })} whileTap={{ scale: 0.95 }}>
                <Button
                  onClick={() =>
                    document
                      .getElementById("pricing")
                      ?.scrollIntoView({ behavior: "smooth" })
                  }
                  className="px-10 py-7 text-xl font-bold bg-yellow-500 hover:bg-yellow-600 text-slate-900 rounded-full shadow-2xl shadow-yellow-500/50 transition-all"
                >
                  <Rocket className="mr-2 w-6 h-6" />
                  Create Your Masterpiece
                </Button>
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* Footer */}
        <Footer />
      </div>
    </>
  );
}