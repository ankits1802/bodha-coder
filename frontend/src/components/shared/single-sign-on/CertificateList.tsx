import { Button } from "@/components/ui/Button";
import { StatusDot } from "@/components/ui/StatusDot";
import type { SsoCertificate } from "@/lib/api/types";
import { formatInstantDay } from "@/lib/format";
import { SSO_TEXT } from "./strings";

interface CertificateListProps {
  certificates: readonly SsoCertificate[];
  onRemove: (value: string) => void;
  now?: Date;
}

export function CertificateList({ certificates, onRemove, now = new Date() }: CertificateListProps) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-subhead font-medium text-label">{SSO_TEXT.certificates}</span>
      <ul aria-label={SSO_TEXT.certificateList} className="m-0 flex list-none flex-col gap-2 p-0">
        {certificates.map((certificate) => {
          const expired = new Date(certificate.expires_at) <= now;
          const day = formatInstantDay(certificate.expires_at);
          return (
            <li key={certificate.value} className="flex flex-wrap items-center justify-between gap-3 rounded-nav bg-control px-3 py-2">
              <div className="flex min-w-0 flex-col gap-0.5">
                <span className="text-body break-all">{certificate.subject || certificate.sha256}</span>
                <span className="font-mono text-caption break-all text-secondary">{certificate.sha256}</span>
                <StatusDot tone={expired ? "bad" : "ok"}>{expired ? SSO_TEXT.expired(day) : SSO_TEXT.expires(day)}</StatusDot>
              </div>
              <Button
                variant="plain"
                size="sm"
                disabled={certificates.length < 2}
                aria-label={SSO_TEXT.removeCertificate(certificate.subject || certificate.sha256)}
                onClick={() => onRemove(certificate.value)}
              >
                {SSO_TEXT.remove}
              </Button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
