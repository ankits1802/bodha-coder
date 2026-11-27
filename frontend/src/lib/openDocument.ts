import { UserFacingError } from "@/lib/api/errors";

export const POPUP_BLOCKED = "Allow pop-ups for Bodha Assure to open the PDF.";

export async function openDocument(loadUrl: () => Promise<{ url: string }>): Promise<void> {
  const tab = window.open("about:blank", "_blank");
  if (!tab) throw new UserFacingError(POPUP_BLOCKED);
  try {
    const { url } = await loadUrl();
    tab.opener = null;
    tab.location.replace(url);
  } catch (error) {
    tab.close();
    throw error;
  }
}
