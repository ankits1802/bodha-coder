const CODE_LENGTH = 12;
const CODE_GROUP = 4;
const CODE_LETTERS = /^[ABCDEFGHJKMNPQRSTVWXYZ2-9]+$/;

export function normalCode(text: string): string | null {
  const bare = text.replace(/[\s-]+/g, "").toUpperCase();
  if (bare.length !== CODE_LENGTH || !CODE_LETTERS.test(bare)) return null;
  return [0, CODE_GROUP, CODE_GROUP * 2].map((start) => bare.slice(start, start + CODE_GROUP)).join("-");
}

export async function sha256Hex(file: Blob): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}
