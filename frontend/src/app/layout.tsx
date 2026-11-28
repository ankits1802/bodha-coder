import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { cookies } from "next/headers";
import { connection } from "next/server";
import type { ReactNode } from "react";
import { SHARED_TEXT } from "@/components/shared/strings";
import { APPEARANCE_COOKIE, appearanceAttributes, appearanceFromCookie } from "@/lib/appearance";
import { encodeSettings, REPORT_ATTRIBUTE, reportSettingsFrom } from "@/lib/errorReports/settings";
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

export default async function RootLayout({ children }: { children: ReactNode }) {
  await connection();
  const reports = { [REPORT_ATTRIBUTE]: encodeSettings(reportSettingsFrom(process.env)) };
  const appearance = appearanceFromCookie((await cookies()).get(APPEARANCE_COOKIE)?.value);
  return (
    <html lang="en" className={inter.variable} {...reports} {...appearanceAttributes(appearance)}>
      <body>{children}</body>
    </html>
  );
}
