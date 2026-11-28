import type { Appearance, MotionChoice, TextSize, Theme } from "@/lib/api/types";

export const APPEARANCE_COOKIE = "bodha_appearance";
export const APPEARANCE_KEY = "appearance";
export const APPEARANCE_KEEP_SECONDS = 300;
export const SYSTEM_APPEARANCE: Appearance = { theme: "system", text_size: "default", reduce_motion: "system" };
export const THEMES: readonly Theme[] = ["system", "light", "dark"];
export const TEXT_SIZES: readonly TextSize[] = ["default", "large", "larger"];
export const MOTION_CHOICES: readonly MotionChoice[] = ["system", "on", "off"];

const COOKIE_SECONDS = 400 * 24 * 60 * 60;
const SEPARATOR = ".";
const ATTRIBUTE_NAMES = ["data-theme", "data-text-size", "data-motion"] as const;
const MOTION_ATTRIBUTES = { system: null, on: "reduce", off: "full" } as const satisfies Record<MotionChoice, string | null>;

type MotionAttribute = NonNullable<(typeof MOTION_ATTRIBUTES)[MotionChoice]>;

export interface AppearanceAttributes {
  "data-theme"?: Exclude<Theme, "system">;
  "data-text-size"?: Exclude<TextSize, "default">;
  "data-motion"?: MotionAttribute;
}

function oneOf<T extends string>(allowed: readonly T[], value: string | undefined): T | undefined {
  return allowed.find((choice) => choice === value);
}

export function appearanceFromCookie(value: string | undefined): Appearance {
  const [theme, textSize, motion] = (value ?? "").split(SEPARATOR);
  return {
    theme: oneOf(THEMES, theme) ?? SYSTEM_APPEARANCE.theme,
    text_size: oneOf(TEXT_SIZES, textSize) ?? SYSTEM_APPEARANCE.text_size,
    reduce_motion: oneOf(MOTION_CHOICES, motion) ?? SYSTEM_APPEARANCE.reduce_motion,
  };
}

export function appearanceCookieValue(appearance: Appearance): string {
  return [appearance.theme, appearance.text_size, appearance.reduce_motion].join(SEPARATOR);
}

export function appearanceAttributes(appearance: Appearance): AppearanceAttributes {
  const attributes: AppearanceAttributes = {};
  if (appearance.theme !== "system") attributes["data-theme"] = appearance.theme;
  if (appearance.text_size !== "default") attributes["data-text-size"] = appearance.text_size;
  const motion = MOTION_ATTRIBUTES[appearance.reduce_motion];
  if (motion) attributes["data-motion"] = motion;
  return attributes;
}

export function applyAppearance(appearance: Appearance, root: HTMLElement = document.documentElement): void {
  const attributes = appearanceAttributes(appearance);
  for (const name of ATTRIBUTE_NAMES) {
    const value = attributes[name];
    if (value) root.setAttribute(name, value);
    else root.removeAttribute(name);
  }
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${APPEARANCE_COOKIE}=${appearanceCookieValue(appearance)}; Path=/; Max-Age=${COOKIE_SECONDS}; SameSite=Lax${secure}`;
}

export function chosenMotion(): MotionChoice {
  if (typeof document === "undefined") return SYSTEM_APPEARANCE.reduce_motion;
  const shown = document.documentElement.getAttribute("data-motion");
  return MOTION_CHOICES.find((choice) => MOTION_ATTRIBUTES[choice] === shown) ?? SYSTEM_APPEARANCE.reduce_motion;
}
