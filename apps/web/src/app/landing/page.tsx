"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Zap,
  Sparkles,
  CheckCircle2,
  ArrowRight,
  Clock,
  Palette,
  Code,
  Rocket,
  Star,
  Globe,
  Users,
  TrendingUp
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";

export default function LandingPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    company: "",
    phone: "",
    projectDetails: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      // Submit lead data to backend
      const response = await fetch("/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to submit form");
      }

      // Redirect to Stripe payment
      const paymentLink = process.env.NEXT_PUBLIC_STRIPE_PAYMENT_LINK;
      if (paymentLink && paymentLink !== "#") {
        window.location.href = paymentLink;
      } else {
        // Fallback if payment link not configured
        alert("Thank you! We'll contact you within 24 hours.");
        setFormData({
          name: "",
          email: "",
          company: "",
          phone: "",
          projectDetails: "",
        });
        setIsSubmitting(false);
      }
    } catch (error) {
      console.error("Error submitting form:", error);
      setSubmitError(
        error instanceof Error ? error.message : "Failed to submit form. Please try again."
      );
      setIsSubmitting(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

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
              validFrom: new Date().toISOString(),
            },
            areaServed: {
              "@type": "Place",
              name: "Worldwide",
            },
          }),
        }}
      />

      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white overflow-hidden">
        {/* Animated Background */}
      <div className="fixed inset-0 opacity-30">
        <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]" />
        <motion.div
          className="absolute top-0 -left-4 w-96 h-96 bg-yellow-500/30 rounded-full mix-blend-multiply filter blur-3xl"
          animate={{
            x: [0, 100, 0],
            y: [0, 50, 0],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
        <motion.div
          className="absolute top-0 right-4 w-96 h-96 bg-purple-500/20 rounded-full mix-blend-multiply filter blur-3xl"
          animate={{
            x: [0, -100, 0],
            y: [0, 100, 0],
          }}
          transition={{
            duration: 25,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      </div>

      {/* Hero Section */}
      <section className="relative px-6 pt-20 pb-32">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: "spring" }}
              className="inline-flex items-center gap-2 px-4 py-2 mb-8 bg-yellow-500/10 border border-yellow-500/20 rounded-full"
            >
              <Sparkles className="w-4 h-4 text-yellow-500" />
              <span className="text-sm font-medium text-yellow-500">
                Premium Website Generation
              </span>
            </motion.div>

            <h1 className="text-6xl md:text-8xl font-bold mb-6 bg-gradient-to-r from-white via-yellow-100 to-white bg-clip-text text-transparent">
              Your Website.
              <br />
              <span className="text-yellow-500">In 3 Days.</span>
            </h1>

            <p className="text-xl md:text-2xl text-slate-300 mb-12 max-w-3xl mx-auto">
              Professional websites and landing pages delivered at lightning speed.
              No meetings. No hassle. Just results.
            </p>

            <motion.div
              whileHover={{ scale: 1.05 }}
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
                Get Started Now
                <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
            </motion.div>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.8 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-8 mt-24 max-w-4xl mx-auto"
          >
            {[
              { icon: Clock, label: "3 Days", value: "Delivery" },
              { icon: Users, label: "500+", value: "Clients" },
              { icon: Star, label: "5.0", value: "Rating" },
              { icon: TrendingUp, label: "98%", value: "Satisfaction" },
            ].map((stat, i) => (
              <motion.div
                key={i}
                whileHover={{ scale: 1.05 }}
                className="text-center p-6 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10"
              >
                <stat.icon className="w-8 h-8 mx-auto mb-3 text-yellow-500" />
                <div className="text-3xl font-bold text-white">{stat.label}</div>
                <div className="text-sm text-slate-400">{stat.value}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative px-6 py-24 bg-slate-900/50">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-5xl font-bold mb-4">
              Why Choose <span className="text-yellow-500">Us?</span>
            </h2>
            <p className="text-xl text-slate-400">
              We handle everything while you focus on your business
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Zap,
                title: "Lightning Fast",
                description:
                  "Get your professional website in just 3 days. No endless revisions, no delays.",
                color: "yellow",
              },
              {
                icon: Palette,
                title: "Custom Design",
                description:
                  "Every website is uniquely crafted to match your brand and vision perfectly.",
                color: "purple",
              },
              {
                icon: Code,
                title: "Premium Tech",
                description:
                  "Built with cutting-edge technology on our proprietary platform for optimal performance.",
                color: "blue",
              },
              {
                icon: Rocket,
                title: "Ready to Launch",
                description:
                  "Delivered complete and ready to go live. Hosting, SSL, and optimization included.",
                color: "green",
              },
              {
                icon: Globe,
                title: "SEO Optimized",
                description:
                  "Built for search engines from the ground up. Get found by your customers.",
                color: "pink",
              },
              {
                icon: Users,
                title: "Direct Support",
                description:
                  "Talk directly with us. No ticketing systems, no chatbots. Just real people.",
                color: "orange",
              },
            ].map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
                viewport={{ once: true }}
                whileHover={{ y: -10, scale: 1.02 }}
              >
                <Card className="p-8 h-full bg-white/5 backdrop-blur-sm border-white/10 hover:border-yellow-500/50 transition-all hover:shadow-2xl hover:shadow-yellow-500/20">
                  <div className="mb-4">
                    <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-yellow-500/20 to-yellow-600/20 flex items-center justify-center">
                      <feature.icon className="w-7 h-7 text-yellow-500" />
                    </div>
                  </div>
                  <h3 className="text-2xl font-bold mb-3 text-white">
                    {feature.title}
                  </h3>
                  <p className="text-slate-400 leading-relaxed">
                    {feature.description}
                  </p>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="relative px-6 py-24">
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
            {/* Connection Line */}
            <div className="hidden lg:block absolute top-24 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-yellow-500/50 to-transparent" />

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
                viewport={{ once: true }}
                className="relative"
              >
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  className="text-center"
                >
                  <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-yellow-500 to-yellow-600 flex items-center justify-center text-2xl font-bold shadow-2xl shadow-yellow-500/50 relative z-10">
                    {process.step}
                  </div>
                  <div className="mb-4 flex justify-center">
                    <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center border border-white/10">
                      <process.icon className="w-6 h-6 text-yellow-500" />
                    </div>
                  </div>
                  <h3 className="text-xl font-bold mb-3 text-white">
                    {process.title}
                  </h3>
                  <p className="text-slate-400 leading-relaxed text-sm">
                    {process.description}
                  </p>
                </motion.div>
              </motion.div>
            ))}
          </div>

          {/* Timeline */}
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
      <section className="relative px-6 py-24 bg-slate-900/50">
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
              One price. Everything you need.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-4">
            {[
              "Professional custom design",
              "Mobile-responsive layout",
              "Lightning-fast performance",
              "SEO optimization",
              "SSL certificate included",
              "Contact forms & integrations",
              "Google Analytics setup",
              "Social media integration",
              "Premium hosting (1 year)",
              "Content management system",
              "Performance monitoring",
              "Free minor updates (30 days)",
            ].map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05, duration: 0.3 }}
                viewport={{ once: true }}
                whileHover={{ x: 10 }}
                className="flex items-center gap-3 p-4 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 hover:border-yellow-500/50 transition-all"
              >
                <CheckCircle2 className="w-6 h-6 text-yellow-500 flex-shrink-0" />
                <span className="text-lg text-white">{item}</span>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing & CTA */}
      <section id="pricing" className="relative px-6 py-24">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-start">
            {/* Pricing Card */}
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
            >
              <Card className="p-10 bg-gradient-to-br from-yellow-500/10 to-yellow-600/5 border-2 border-yellow-500/50 shadow-2xl shadow-yellow-500/20">
                <div className="text-center mb-8">
                  <div className="inline-flex items-center gap-2 px-4 py-2 mb-6 bg-yellow-500 rounded-full">
                    <Star className="w-4 h-4 text-slate-900" />
                    <span className="text-sm font-bold text-slate-900">
                      LIMITED TIME OFFER
                    </span>
                  </div>
                  <div className="mb-4">
                    <div className="text-5xl font-bold text-white mb-2">
                      $1,000
                    </div>
                    <div className="text-slate-400">One-time payment</div>
                  </div>
                  <div className="text-sm text-yellow-500 font-semibold">
                    Regular price: $2,500
                  </div>
                </div>

                <div className="space-y-4 mb-8">
                  {[
                    "Complete website in 3 days",
                    "Custom design & development",
                    "All features included",
                    "1 year premium hosting",
                    "Direct support access",
                    "30-day update guarantee",
                  ].map((feature, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <CheckCircle2 className="w-5 h-5 text-yellow-500 flex-shrink-0" />
                      <span className="text-white">{feature}</span>
                    </div>
                  ))}
                </div>

                <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                  <Button
                    onClick={() =>
                      window.open(
                        process.env.NEXT_PUBLIC_STRIPE_PAYMENT_LINK || "#",
                        "_blank"
                      )
                    }
                    className="w-full py-6 text-lg font-bold bg-yellow-500 hover:bg-yellow-600 text-slate-900 rounded-xl shadow-2xl shadow-yellow-500/50 transition-all"
                  >
                    <Zap className="mr-2 w-5 h-5" />
                    Start Your Project Now
                  </Button>
                </motion.div>

                <p className="text-center text-sm text-slate-400 mt-6">
                  Secure payment via Stripe • Money-back guarantee
                </p>
              </Card>
            </motion.div>

            {/* Contact Form */}
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
            >
              <div className="sticky top-8">
                <h3 className="text-3xl font-bold mb-2 text-white">
                  Get Started Today
                </h3>
                <p className="text-slate-400 mb-8">
                  Fill out the form and we&apos;ll reach out within 24 hours
                </p>

                <form onSubmit={handleSubmit} className="space-y-6">
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

                  <div>
                    <label className="block text-sm font-medium mb-2 text-white">
                      Company
                    </label>
                    <Input
                      type="text"
                      name="company"
                      value={formData.company}
                      onChange={handleChange}
                      placeholder="Your Company Inc."
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
                      rows={5}
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
                      className="w-full py-6 text-lg font-semibold bg-white/10 hover:bg-white/20 text-white border border-white/20 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSubmitting ? "Submitting..." : "Submit & Continue to Payment"}
                      <ArrowRight className="ml-2 w-5 h-5" />
                    </Button>
                  </motion.div>

                  <p className="text-xs text-center text-slate-500">
                    By submitting, you agree to our terms of service
                  </p>
                </form>
              </div>
            </motion.div>
          </div>
        </div>
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
              Ready to Launch Your
              <br />
              <span className="text-yellow-500">Dream Website?</span>
            </h2>
            <p className="text-xl text-slate-300 mb-10">
              Join hundreds of satisfied clients who transformed their online presence
            </p>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button
                onClick={() =>
                  document
                    .getElementById("pricing")
                    ?.scrollIntoView({ behavior: "smooth" })
                }
                className="px-10 py-7 text-xl font-bold bg-yellow-500 hover:bg-yellow-600 text-slate-900 rounded-full shadow-2xl shadow-yellow-500/50 transition-all"
              >
                <Rocket className="mr-2 w-6 h-6" />
                Start Your Project
              </Button>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative px-6 py-12 border-t border-white/10">
        <div className="max-w-7xl mx-auto text-center text-slate-400">
          <p className="mb-2">
            © {new Date().getFullYear()} Lenquant. All rights reserved.
          </p>
          <p className="text-sm">
            Premium websites delivered in 3 days or less.
          </p>
        </div>
      </footer>
      </div>
    </>
  );
}
