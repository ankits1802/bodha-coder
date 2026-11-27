"use client";

import { ReasonPicker, type ReasonPickerProps } from "@/components/shared/reason-picker/ReasonPicker";
import type { OverrideReason } from "@/lib/api/types";
import { OVERRIDE_REASONS } from "../overrideReasons";
import { REVIEW_TEXT } from "../strings";

type OverrideReasonPickerProps = Omit<ReasonPickerProps<OverrideReason>, "reasons" | "labels">;

export function OverrideReasonPicker(props: OverrideReasonPickerProps) {
  return <ReasonPicker {...props} reasons={OVERRIDE_REASONS} labels={REVIEW_TEXT.override.reasons} />;
}
