"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Mail,
  Phone,
  Building2,
  Calendar,
  DollarSign,
  CheckCircle2,
  Clock,
  XCircle,
  ExternalLink
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageFrame } from "@/components/shell/page-frame";
import { LoadingState } from "@/components/state/loading-state";
import { EmptyState } from "@/components/state/empty-state";
import { ErrorState } from "@/components/state/error-state";

interface LandingLead {
  _id: string;
  name: string;
  email: string;
  company: string | null;
  phone: string | null;
  projectDetails: string;
  source: string;
  status: string;
  paymentStatus: string;
  orderType: string;
  price: number;
  currency: string;
  createdAt: string;
  updatedAt: string;
  selectedServices?: { [key: string]: number };
  lineItems?: Array<{
    id: string;
    name: string;
    price: number;
    quantity: number;
    billingCycle: "one-time" | "monthly";
  }>;
  metadata?: {
    userAgent?: string | null;
    referrer?: string | null;
    ipAddress?: string | null;
  };
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatCurrency(amount: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency,
  }).format(amount);
}

function getStatusBadge(status: string) {
  switch (status) {
    case "pending":
      return <Badge className="border-yellow-500/40 bg-yellow-500/10 text-yellow-100"><Clock className="mr-1 h-3 w-3" />Pending</Badge>;
    case "contacted":
      return <Badge className="border-blue-500/40 bg-blue-500/10 text-blue-100"><Mail className="mr-1 h-3 w-3" />Contacted</Badge>;
    case "in_progress":
      return <Badge className="border-purple-500/40 bg-purple-500/10 text-purple-100"><Clock className="mr-1 h-3 w-3" />In Progress</Badge>;
    case "completed":
      return <Badge className="border-emerald-500/40 bg-emerald-500/10 text-emerald-100"><CheckCircle2 className="mr-1 h-3 w-3" />Completed</Badge>;
    case "cancelled":
      return <Badge className="border-rose-500/40 bg-rose-500/10 text-rose-100"><XCircle className="mr-1 h-3 w-3" />Cancelled</Badge>;
    default:
      return <Badge>{status}</Badge>;
  }
}

function getPaymentBadge(paymentStatus: string) {
  switch (paymentStatus) {
    case "paid":
      return <Badge className="border-emerald-500/40 bg-emerald-500/10 text-emerald-100"><CheckCircle2 className="mr-1 h-3 w-3" />Paid</Badge>;
    case "unpaid":
      return <Badge className="border-rose-500/40 bg-rose-500/10 text-rose-100"><XCircle className="mr-1 h-3 w-3" />Unpaid</Badge>;
    case "refunded":
      return <Badge className="border-gray-500/40 bg-gray-500/10 text-gray-100">Refunded</Badge>;
    default:
      return <Badge>{paymentStatus}</Badge>;
  }
}

export default function OrdersPage() {
  const [leads, setLeads] = useState<LandingLead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedLead, setSelectedLead] = useState<LandingLead | null>(null);

  useEffect(() => {
    async function fetchLeads() {
      try {
        const response = await fetch("/api/landing-leads");
        if (!response.ok) {
          throw new Error("Failed to fetch leads");
        }
        const data = await response.json();
        setLeads(data.leads || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load orders");
      } finally {
        setLoading(false);
      }
    }

    fetchLeads();
  }, []);

  async function updateLeadStatus(id: string, status: string) {
    try {
      const response = await fetch(`/api/landing-leads/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });

      if (!response.ok) {
        throw new Error("Failed to update status");
      }

      // Refresh leads
      setLeads(leads.map((lead) =>
        lead._id === id ? { ...lead, status, updatedAt: new Date().toISOString() } : lead
      ));
    } catch (err) {
      console.error("Error updating status:", err);
      alert("Failed to update status");
    }
  }

  async function updatePaymentStatus(id: string, paymentStatus: string) {
    try {
      const response = await fetch(`/api/landing-leads/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paymentStatus }),
      });

      if (!response.ok) {
        throw new Error("Failed to update payment status");
      }

      // Refresh leads
      setLeads(leads.map((lead) =>
        lead._id === id ? { ...lead, paymentStatus, updatedAt: new Date().toISOString() } : lead
      ));
    } catch (err) {
      console.error("Error updating payment status:", err);
      alert("Failed to update payment status");
    }
  }

  // Calculate monthly recurring revenue
  const monthlyRecurring = leads
    .filter((l) => l.paymentStatus === "paid" && l.lineItems)
    .reduce((sum, l) => {
      const monthlyItems = l.lineItems?.filter((item) => item.billingCycle === "monthly") || [];
      const monthlyTotal = monthlyItems.reduce((itemSum, item) => itemSum + item.price * item.quantity, 0);
      return sum + monthlyTotal;
    }, 0);

  const stats = {
    total: leads.length,
    pending: leads.filter((l) => l.status === "pending").length,
    paid: leads.filter((l) => l.paymentStatus === "paid").length,
    totalRevenue: leads
      .filter((l) => l.paymentStatus === "paid")
      .reduce((sum, l) => sum + l.price, 0),
    monthlyRecurring,
  };

  return (
    <PageFrame
      eyebrow="Orders"
      title="Landing Page Orders"
      description="Manage customer orders from the landing page. Track payments, project status, and client communications."
    >
      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader>
            <CardDescription>Total Orders</CardDescription>
            <CardTitle className="text-3xl">{stats.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Pending</CardDescription>
            <CardTitle className="text-3xl">{stats.pending}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Paid</CardDescription>
            <CardTitle className="text-3xl">{stats.paid}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Total Revenue</CardDescription>
            <CardTitle className="text-3xl">{formatCurrency(stats.totalRevenue, "USD")}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Monthly Recurring</CardDescription>
            <CardTitle className="text-3xl">{formatCurrency(stats.monthlyRecurring, "USD")}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {error ? (
        <ErrorState title="Error loading orders" description={error} />
      ) : null}

      {/* Orders List */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Orders</CardTitle>
          <CardDescription>All orders from the landing page</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <LoadingState label="Loading orders..." />
          ) : leads.length === 0 ? (
            <EmptyState
              title="No orders yet"
              description="Orders will appear here when customers submit the landing page form."
            />
          ) : (
            <div className="space-y-4">
              {leads.map((lead) => (
                <div
                  key={lead._id}
                  className="rounded-2xl border border-line bg-panel p-6 hover:border-accent/50 transition-colors cursor-pointer"
                  onClick={() => setSelectedLead(selectedLead?._id === lead._id ? null : lead)}
                >
                  {/* Header */}
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex-1">
                      <div className="flex items-start gap-3">
                        <div className="flex-1">
                          <h3 className="text-lg font-semibold text-text">{lead.name}</h3>
                          <div className="mt-1 flex flex-wrap gap-2 text-sm text-muted">
                            <span className="flex items-center gap-1">
                              <Mail className="h-3.5 w-3.5" />
                              {lead.email}
                            </span>
                            {lead.company && (
                              <span className="flex items-center gap-1">
                                <Building2 className="h-3.5 w-3.5" />
                                {lead.company}
                              </span>
                            )}
                            {lead.phone && (
                              <span className="flex items-center gap-1">
                                <Phone className="h-3.5 w-3.5" />
                                {lead.phone}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col gap-2">
                      <div className="flex flex-wrap gap-2">
                        {getStatusBadge(lead.status)}
                        {getPaymentBadge(lead.paymentStatus)}
                        <Badge className="border-accent/40 bg-accent/10 text-accent">
                          <DollarSign className="mr-1 h-3 w-3" />
                          {formatCurrency(lead.price, lead.currency)}
                        </Badge>
                      </div>
                      {/* Inline service summary */}
                      {lead.lineItems && lead.lineItems.length > 1 && (
                        <div className="text-xs text-muted">
                          {lead.lineItems.slice(1).map((item, idx) => (
                            <span key={idx}>
                              {idx > 0 && ", "}
                              {item.quantity > 1 ? `${item.quantity}x ` : ""}
                              {item.name}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Metadata */}
                  <div className="mt-3 flex flex-wrap gap-4 text-xs text-muted">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3.5 w-3.5" />
                      {formatDate(lead.createdAt)}
                    </span>
                    <Badge className="text-xs">
                      {lead.source}
                    </Badge>
                    <Badge className="text-xs">
                      {lead.orderType}
                    </Badge>
                  </div>

                  {/* Expanded Details */}
                  {selectedLead?._id === lead._id && (
                    <div className="mt-6 space-y-4 border-t border-line pt-6">
                      {/* Order Items Breakdown */}
                      {lead.lineItems && lead.lineItems.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold text-text mb-2">Order Items</h4>
                          <div className="space-y-2">
                            {lead.lineItems.map((item, i) => (
                              <div key={i} className="flex justify-between text-sm">
                                <span className="text-muted">
                                  {item.quantity > 1 ? `${item.quantity}x ` : ""}{item.name}
                                  <Badge className="ml-2 text-[10px]">
                                    {item.billingCycle === "monthly" ? "MONTHLY" : "ONE-TIME"}
                                  </Badge>
                                </span>
                                <span className="font-medium text-text">
                                  ${(item.price * item.quantity).toLocaleString()}
                                </span>
                              </div>
                            ))}
                            <div className="border-t border-line pt-2 mt-2 flex justify-between text-base font-bold">
                              <span>Total</span>
                              <span className="text-accent">{formatCurrency(lead.price, lead.currency)}</span>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Project Details */}
                      <div>
                        <h4 className="text-sm font-semibold text-text mb-2">Project Details</h4>
                        <p className="text-sm text-muted leading-relaxed whitespace-pre-wrap">
                          {lead.projectDetails}
                        </p>
                      </div>

                      {/* Metadata */}
                      {lead.metadata && (
                        <div>
                          <h4 className="text-sm font-semibold text-text mb-2">Technical Details</h4>
                          <div className="grid gap-2 text-xs text-muted">
                            {lead.metadata.ipAddress && (
                              <div>IP: {lead.metadata.ipAddress}</div>
                            )}
                            {lead.metadata.referrer && (
                              <div>Referrer: {lead.metadata.referrer}</div>
                            )}
                            {lead.metadata.userAgent && (
                              <div className="break-all">User Agent: {lead.metadata.userAgent}</div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Actions */}
                      <div className="flex flex-wrap gap-2 pt-4 border-t border-line">
                        <div className="flex-1">
                          <label className="text-xs text-muted mb-1 block">Order Status</label>
                          <select
                            value={lead.status}
                            onChange={(e) => updateLeadStatus(lead._id, e.target.value)}
                            className="px-3 py-2 rounded-lg bg-panel-2 border border-line text-sm text-text"
                          >
                            <option value="pending">Pending</option>
                            <option value="contacted">Contacted</option>
                            <option value="in_progress">In Progress</option>
                            <option value="completed">Completed</option>
                            <option value="cancelled">Cancelled</option>
                          </select>
                        </div>

                        <div className="flex-1">
                          <label className="text-xs text-muted mb-1 block">Payment Status</label>
                          <select
                            value={lead.paymentStatus}
                            onChange={(e) => updatePaymentStatus(lead._id, e.target.value)}
                            className="px-3 py-2 rounded-lg bg-panel-2 border border-line text-sm text-text"
                          >
                            <option value="unpaid">Unpaid</option>
                            <option value="paid">Paid</option>
                            <option value="refunded">Refunded</option>
                          </select>
                        </div>

                        <div className="flex items-end gap-2">
                          <Button
                            variant="secondary"
                            onClick={() => window.open(`mailto:${lead.email}`, "_blank")}
                          >
                            <Mail className="mr-2 h-4 w-4" />
                            Email Client
                          </Button>
                          {lead.phone && (
                            <Button
                              variant="secondary"
                              onClick={() => window.open(`tel:${lead.phone}`, "_blank")}
                            >
                              <Phone className="mr-2 h-4 w-4" />
                              Call
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </PageFrame>
  );
}
