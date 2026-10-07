export const DEFAULT_BOOKING_URL =
  "https://calendly.com/lengrowth/lenquant-new-website";

export function resolveBookingUrl(url?: string | null): string {
  const value = url?.trim();
  return !value || value === "https://calendly.com/lenquant/sites"
    ? DEFAULT_BOOKING_URL
    : value;
}
