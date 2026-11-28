import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

const BLOCKING_IMPACTS = new Set(["serious", "critical"]);
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const SNIPPET_LENGTH = 240;
const SOME_TEXT = new RegExp("\\S");

export async function expectAccessible(page: Page): Promise<void> {
  await expect(page, "the page has a title once its metadata has streamed in").toHaveTitle(SOME_TEXT);
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  const blocking = results.violations
    .filter((violation) => BLOCKING_IMPACTS.has(violation.impact ?? ""))
    .map((violation) => ({
      rule: violation.id,
      impact: violation.impact,
      help: violation.help,
      nodes: violation.nodes.map((node) => ({
        target: node.target.join(" "),
        html: node.html.slice(0, SNIPPET_LENGTH),
        why: node.failureSummary,
      })),
    }));
  expect(blocking, `serious or critical accessibility violations on ${new URL(page.url()).pathname}`).toEqual([]);
}
