import type { Channel } from "@/lib/api/types";

const EMAIL: Channel = "email";

export function isOfferedChannel(channel: Channel, canSendTexts: boolean): boolean {
  return canSendTexts || channel === EMAIL;
}

export function usableChannel(preferred: Channel, canSendTexts: boolean): Channel {
  return isOfferedChannel(preferred, canSendTexts) ? preferred : EMAIL;
}
