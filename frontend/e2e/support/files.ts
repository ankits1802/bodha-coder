import { readFile } from "node:fs/promises";
import path from "node:path";
import type { Page } from "@playwright/test";

interface DroppedFile {
  name: string;
  base64: string;
}

export async function dropFiles(page: Page, paths: readonly string[]): Promise<void> {
  const files: DroppedFile[] = await Promise.all(
    paths.map(async (file) => ({ name: path.basename(file), base64: (await readFile(file)).toString("base64") })),
  );
  const transfer = await page.evaluateHandle((chosen: DroppedFile[]) => {
    const data = new DataTransfer();
    for (const file of chosen) {
      const bytes = Uint8Array.from(atob(file.base64), (character) => character.charCodeAt(0));
      data.items.add(new File([bytes], file.name, { type: "application/pdf" }));
    }
    return data;
  }, files);
  await page.dispatchEvent("body", "dragenter", { dataTransfer: transfer });
  await page.dispatchEvent("body", "drop", { dataTransfer: transfer });
}
