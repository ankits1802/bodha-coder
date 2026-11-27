export function leaveFor(url: string): void {
  if (new URL(url).protocol !== "https:") throw new Error("refusing to leave for a link that is not https");
  window.location.assign(url);
}
