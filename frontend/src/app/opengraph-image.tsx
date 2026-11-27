import { ImageResponse } from "next/og";
import { SHARED_TEXT } from "@/components/shared/strings";

export const alt = SHARED_TEXT.meta.shareAlt;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const CODES = [
  { code: "99214", dot: "#34C759" },
  { code: "E11.65", dot: "#34C759" },
  { code: "I12.9", dot: "#34C759" },
  { code: "N18.30", dot: "#FF9F0A" },
];

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", padding: 88, background: "#FAFAF8", color: "#1D1D1F" }}>
        <div style={{ fontSize: 34, fontWeight: 600 }}>{SHARED_TEXT.brand}</div>
        <div style={{ display: "flex", flexWrap: "wrap", marginTop: 30, fontSize: 92, fontWeight: 700, letterSpacing: "-0.035em", lineHeight: 1.02 }}>
          <span>Bill the level you can&nbsp;</span>
          <span style={{ background: "rgba(52,199,89,0.22)", borderBottom: "7px solid #34C759" }}>defend.</span>
        </div>
        <div style={{ display: "flex", gap: 16, marginTop: 56 }}>
          {CODES.map((item) => (
            <div key={item.code} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 22px", borderRadius: 999, background: "#FFFFFF", fontSize: 30, fontWeight: 600, boxShadow: "0 0 0 1px rgba(0,0,0,0.07)" }}>
              <div style={{ width: 13, height: 13, borderRadius: 999, background: item.dot }} />
              {item.code}
            </div>
          ))}
        </div>
      </div>
    ),
    size,
  );
}
