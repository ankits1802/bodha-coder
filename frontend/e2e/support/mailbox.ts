import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { expect } from "@playwright/test";

export interface Message {
  to: string;
  subject: string;
  body: string;
  sms: boolean;
}

const OUTBOX_WAIT_MS = 30_000;

function outboxFolder(): string {
  const folder = process.env.MAIL_OUTBOX_DIR;
  if (!folder) throw new Error("set MAIL_OUTBOX_DIR to the folder the API writes messages to");
  return folder;
}

function parsed(text: string): Message {
  const [head = "", ...rest] = text.split("\n\n");
  const [toLine = "", second = ""] = head.split("\n");
  return {
    to: toLine.replace(/^To: /, ""),
    subject: second === "SMS" ? "" : second.replace(/^Subject: /, ""),
    body: rest.join("\n\n").trim(),
    sms: second === "SMS",
  };
}

async function messagesTo(address: string): Promise<Message[]> {
  const folder = outboxFolder();
  const names = (await readdir(folder).catch(() => [])).filter((name) => name.endsWith(".txt")).sort();
  const messages = await Promise.all(names.map(async (name) => parsed(await readFile(path.join(folder, name), "utf8"))));
  return messages.filter((message) => message.to.toLowerCase() === address.toLowerCase());
}

export async function nextMessage(address: string, matches: (message: Message) => boolean, seen = 0): Promise<Message> {
  let found: Message | undefined;
  await expect
    .poll(
      async () => {
        found = (await messagesTo(address)).filter(matches)[seen];
        return found !== undefined;
      },
      { message: `a message to ${address}`, timeout: OUTBOX_WAIT_MS },
    )
    .toBe(true);
  return found as Message;
}

export function linkIn(message: Message, pathname: string): string {
  const link = message.body.match(new RegExp(`https?://\\S+${pathname}\\S*`));
  if (!link) throw new Error(`the message "${message.subject}" has no ${pathname} link`);
  return link[0].replace(/[.,]$/, "");
}
