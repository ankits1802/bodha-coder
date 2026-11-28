import { createHmac } from "node:crypto";

const BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
const STEP_SECONDS = 30;
const DIGITS = 6;
const BITS_PER_CHARACTER = 5;
const BITS_PER_BYTE = 8;

function secretBytes(secret: string): Buffer {
  let bits = "";
  for (const character of secret.replace(/=+$/, "").toUpperCase()) {
    const value = BASE32.indexOf(character);
    if (value < 0) throw new Error("the two-step secret is not base32");
    bits += value.toString(2).padStart(BITS_PER_CHARACTER, "0");
  }
  const bytes = [];
  for (let start = 0; start + BITS_PER_BYTE <= bits.length; start += BITS_PER_BYTE) {
    bytes.push(Number.parseInt(bits.slice(start, start + BITS_PER_BYTE), 2));
  }
  return Buffer.from(bytes);
}

export function totpCode(secret: string, at: number = Date.now()): string {
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(at / 1000 / STEP_SECONDS)));
  const digest = createHmac("sha1", secretBytes(secret)).update(counter).digest();
  const offset = (digest.at(-1) ?? 0) & 0x0f;
  const value = (digest.readUInt32BE(offset) & 0x7fffffff) % 10 ** DIGITS;
  return value.toString().padStart(DIGITS, "0");
}
