import type { MetadataRoute } from "next";
import { SHARED_TEXT } from "@/components/shared/strings";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: SHARED_TEXT.brand,
    short_name: SHARED_TEXT.brand,
    description: SHARED_TEXT.meta.description,
    start_url: "/today",
    display: "standalone",
    background_color: "#FAFAF8",
    theme_color: "#FAFAF8",
    icons: [{ src: "/icon.svg", type: "image/svg+xml", sizes: "any" }],
  };
}
