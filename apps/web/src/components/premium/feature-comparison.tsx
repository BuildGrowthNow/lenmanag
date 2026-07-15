"use client";

import { motion } from "framer-motion";
import { Check, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

interface ComparisonFeature {
  name: string;
  values: (boolean | string)[];
}

interface FeatureComparisonProps {
  columns: string[];
  features: ComparisonFeature[];
  highlighted?: number;
  className?: string;
}

export function FeatureComparison({
  columns,
  features,
  highlighted = 1,
  className = "",
}: FeatureComparisonProps) {
  const [hoveredColumn, setHoveredColumn] = useState<number | null>(null);

  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th className="border-b border-border p-4 text-left font-semibold">
              Feature
            </th>
            {columns.map((column, index) => (
              <th
                key={index}
                className={`border-b border-border p-4 text-center font-semibold ${
                  index === highlighted ? "bg-muted" : ""
                } ${hoveredColumn === index ? "bg-muted/50" : ""}`}
                onMouseEnter={() => setHoveredColumn(index)}
                onMouseLeave={() => setHoveredColumn(null)}
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {features.map((feature, featureIndex) => (
            <motion.tr
              key={featureIndex}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: featureIndex * 0.05 }}
            >
              <td className="border-b border-border p-4 font-medium">
                {feature.name}
              </td>
              {feature.values.map((value, valueIndex) => (
                <td
                  key={valueIndex}
                  className={`border-b border-border p-4 text-center ${
                    valueIndex === highlighted ? "bg-muted" : ""
                  } ${hoveredColumn === valueIndex ? "bg-muted/50" : ""}`}
                  onMouseEnter={() => setHoveredColumn(valueIndex)}
                  onMouseLeave={() => setHoveredColumn(null)}
                >
                  {typeof value === "boolean" ? (
                    value ? (
                      <Check className="mx-auto h-5 w-5 text-green-500" />
                    ) : (
                      <X className="mx-auto h-5 w-5 text-red-500" />
                    )
                  ) : (
                    <span>{value}</span>
                  )}
                </td>
              ))}
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface PricingTier {
  name: string;
  price: string;
  description: string;
  features: string[];
  highlighted?: boolean;
  cta: string;
  ctaHref: string;
}

interface PricingComparisonProps {
  tiers: PricingTier[];
  className?: string;
}

export function PricingComparison({ tiers, className = "" }: PricingComparisonProps) {
  return (
    <div className={`grid gap-8 md:grid-cols-${tiers.length} ${className}`}>
      {tiers.map((tier, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: index * 0.1 }}
          className={`relative rounded-lg border p-8 ${
            tier.highlighted
              ? "border-primary shadow-lg"
              : "border-border"
          }`}
        >
          {tier.highlighted && (
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 rounded-full bg-primary px-4 py-1 text-sm font-semibold text-primary-foreground">
              Most Popular
            </div>
          )}
          <div className="mb-4">
            <h3 className="text-2xl font-bold">{tier.name}</h3>
            <div className="mt-2 text-4xl font-bold">{tier.price}</div>
            <p className="mt-2 text-sm text-muted-foreground">{tier.description}</p>
          </div>
          <ul className="mb-6 space-y-3">
            {tier.features.map((feature, featureIndex) => (
              <li key={featureIndex} className="flex items-start gap-2">
                <Check className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-500" />
                <span>{feature}</span>
              </li>
            ))}
          </ul>
          <a href={tier.ctaHref} className="block">
            <Button
              className="w-full"
              variant={tier.highlighted ? "default" : "outline"}
            >
              {tier.cta}
            </Button>
          </a>
        </motion.div>
      ))}
    </div>
  );
}
