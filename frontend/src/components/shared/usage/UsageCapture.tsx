"use client";

import { useEffect } from "react";
import { sendUsage } from "@/lib/api/usage";
import { startUsageCapture } from "@/lib/usage/capture";
import { usageRecorder } from "@/lib/usage/session";

export function UsageCapture() {
  useEffect(() => startUsageCapture(usageRecorder, sendUsage, { window, document }), []);
  return null;
}
