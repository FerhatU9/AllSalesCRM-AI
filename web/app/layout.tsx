import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AllSales CRM | Sales workspace",
  description: "A secure workspace for lead management and sales-policy assistance.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
