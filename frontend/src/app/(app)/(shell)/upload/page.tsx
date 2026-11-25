import type { Metadata } from "next";
import { UploadScreen } from "@/features/upload/UploadScreen";
import { UPLOAD_TEXT } from "@/features/upload/strings";

export const metadata: Metadata = { title: UPLOAD_TEXT.title };

export default function UploadPage() {
  return <UploadScreen />;
}
