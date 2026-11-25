import { Button } from "@/components/ui/Button";
import type { SignedInDevice } from "@/lib/api/types";
import { formatSince } from "@/lib/format";
import { deviceOf } from "./accessLog";
import { SECURITY_TEXT } from "./strings";

interface DeviceListProps {
  devices: SignedInDevice[];
  busyId: string | null;
  onSignOut: (device: SignedInDevice) => void;
}

export function DeviceList({ devices, busyId, onSignOut }: DeviceListProps) {
  const words = SECURITY_TEXT.signedIn;
  return (
    <ul aria-label={words.listLabel} className="m-0 list-none p-0">
      {devices.map((device) => (
        <li
          key={device.id}
          className="flex min-h-13 items-center justify-between gap-4 border-t border-hairline px-4.5 py-2 text-body"
        >
          <span className="flex min-w-0 flex-col">
            <span className="truncate">{deviceOf(device)}</span>
            <span className="text-footnote text-secondary">
              {device.current ? words.thisDevice : formatSince(device.last_used_at)}
            </span>
          </span>
          {device.current ? null : (
            <Button
              size="sm"
              variant="plain"
              pending={busyId === device.id}
              aria-label={words.signOutFor(deviceOf(device))}
              onClick={() => onSignOut(device)}
            >
              {words.signOut}
            </Button>
          )}
        </li>
      ))}
    </ul>
  );
}
