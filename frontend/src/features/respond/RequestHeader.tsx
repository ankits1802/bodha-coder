import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { StatusDot } from "@/components/ui/StatusDot";
import type { ProviderRequest } from "@/lib/api/types";
import { formatCalendarDay, formatDateTime } from "@/lib/format";
import { RESPOND_TEXT } from "./strings";

interface RequestHeaderProps {
  request: ProviderRequest;
  pdfPending: boolean;
  pdfError: string | null;
  onOpenPdf: () => void;
}

function patientLine(request: ProviderRequest): string {
  const { age, sex } = request.patient;
  const person = [age === null ? null : String(age), sex].filter((part) => part !== null && part !== "").join(", ");
  return [person, formatCalendarDay(request.service_date, "long"), request.visit_type, request.place_name]
    .filter(Boolean)
    .join(" · ");
}

function DocumentIcon() {
  return (
    <svg width="14" height="16" viewBox="0 0 14 16" aria-hidden="true">
      <path d="M2 1.5h6.2L12 5.3v9.2H2z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M8 1.5v4h4" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}

export function RequestHeader({ request, pdfPending, pdfError, onOpenPdf }: RequestHeaderProps) {
  return (
    <header className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="m-0 mb-1 text-subhead text-secondary">{RESPOND_TEXT.requestLabel(request.questions.length)}</p>
          <h1 className="m-0 text-large-title font-bold tracking-title">{request.patient.name ?? RESPOND_TEXT.patientUnknown}</h1>
          <p className="mt-1 mb-0 text-body-lg text-secondary">{patientLine(request)}</p>
          <p className="mt-2.5 mb-0 flex flex-wrap gap-x-4.5 gap-y-1.5 text-subhead text-secondary">
            <span>
              {request.requested_by
                ? RESPOND_TEXT.requestedBy(request.requested_by, formatDateTime(request.requested_at))
                : RESPOND_TEXT.requested(formatDateTime(request.requested_at))}
            </span>
            {request.answered_at ? <span>{RESPOND_TEXT.signedAt(formatDateTime(request.answered_at))}</span> : null}
            {request.status === "sent" ? (
              <StatusDot tone="warn" className="text-secondary">
                {RESPOND_TEXT.answerBy(formatDateTime(request.expires_at))}
              </StatusDot>
            ) : null}
          </p>
        </div>
        <Button onClick={onOpenPdf} pending={pdfPending}>
          {pdfPending ? null : <DocumentIcon />}
          {RESPOND_TEXT.openPdf}
        </Button>
      </div>
      {pdfError ? <InlineAlert tone="bad">{pdfError}</InlineAlert> : null}
    </header>
  );
}
