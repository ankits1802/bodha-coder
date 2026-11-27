export type HapticPattern = "tap" | "select" | "success";

const PATTERNS: Record<HapticPattern, number[]> = {
  tap: [8],
  select: [5],
  success: [12, 60, 18],
};

let switchLabel: HTMLLabelElement | null = null;

function hiddenSwitch(): HTMLLabelElement {
  if (switchLabel?.isConnected) return switchLabel;
  const input = document.createElement("input");
  input.type = "checkbox";
  input.tabIndex = -1;
  input.setAttribute("switch", "");
  const label = document.createElement("label");
  label.setAttribute("aria-hidden", "true");
  label.style.cssText = "position:fixed;left:0;top:0;width:1px;height:1px;overflow:hidden;opacity:0;pointer-events:none";
  label.append(input);
  document.body.append(label);
  switchLabel = label;
  return label;
}

export function haptic(pattern: HapticPattern = "tap"): void {
  if (typeof navigator === "undefined") return;
  if (typeof navigator.vibrate === "function") {
    navigator.vibrate(PATTERNS[pattern]);
    return;
  }
  if (navigator.maxTouchPoints > 0) hiddenSwitch().click();
}
