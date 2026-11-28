import { test as base, type BrowserContext, type Cookie } from "@playwright/test";
import { ADMIN_ORIGIN, SITE_ORIGIN } from "../support/app";
import { openSessions } from "../support/seed";
import { sweepWorld, type Who } from "./world";

interface HeldSession {
  name: string;
  path: string;
  value: string;
}

type SessionCookie = Parameters<BrowserContext["addCookies"]>[0][number];

export function originFor(who: Who | null): string {
  return who === "hq" ? ADMIN_ORIGIN : SITE_ORIGIN;
}

function hostFor(who: Who): string {
  return new URL(originFor(who)).hostname;
}

class SessionPool {
  private readonly held = new Map<Who, HeldSession>();

  async cookieFor(who: Who): Promise<SessionCookie> {
    const held = this.held.get(who) ?? (await this.open(who));
    return { ...held, domain: hostFor(who), httpOnly: true, secure: false, sameSite: "Strict" };
  }

  keep(who: Who, cookies: readonly Cookie[]): void {
    const held = this.held.get(who);
    const current = cookies.find(
      (cookie) => cookie.name === held?.name && cookie.path === held.path && cookie.domain === hostFor(who),
    );
    if (held && current) this.held.set(who, { ...held, value: current.value });
  }

  drop(who: Who): void {
    this.held.delete(who);
  }

  private async open(wanted: Who): Promise<HeldSession> {
    const world = await sweepWorld();
    const missing = this.held.size === 0 ? (Object.keys(world.people) as Who[]) : [wanted];
    const opened = await openSessions(missing.map((who) => world.people[who]));
    missing.forEach((who, index) => this.held.set(who, { ...opened.cookie, value: opened.tokens[index] ?? "" }));
    const held = this.held.get(wanted);
    if (!held) throw new Error(`no session was opened for ${wanted}`);
    return held;
  }
}

const pool = new SessionPool();

export const test = base.extend<{ signIn: (who: Who) => Promise<void> }>({
  signIn: async ({ context }, provide, testInfo) => {
    const used = new Set<Who>();
    await provide(async (who) => {
      used.add(who);
      await context.addCookies([await pool.cookieFor(who)]);
    });
    const passed = testInfo.status === testInfo.expectedStatus;
    const cookies = passed ? await context.cookies() : [];
    for (const who of used) {
      if (passed) pool.keep(who, cookies);
      else pool.drop(who);
    }
  },
});

export { expect } from "@playwright/test";
