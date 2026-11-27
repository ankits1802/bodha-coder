import type { Metadata } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";
import { SHARED_TEXT } from "@/components/shared/strings";
import { siteUrl } from "@/lib/site";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl()),
  title: { default: SHARED_TEXT.brand, template: `%s · ${SHARED_TEXT.brand}` },
  description: SHARED_TEXT.meta.description,
  applicationName: SHARED_TEXT.brand,
  openGraph: { type: "website", siteName: SHARED_TEXT.brand, description: SHARED_TEXT.meta.description },
  twitter: { card: "summary_large_image" },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>{children}</body>
    </html>
  );
}
