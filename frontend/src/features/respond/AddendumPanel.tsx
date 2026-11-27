import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel } from "@/components/ui/Panel";
import { RESPOND_TEXT } from "./strings";

interface AddendumPanelProps {
  header: string;
  lines: string[];
  confirmed: boolean;
  onConfirm: (confirmed: boolean) => void;
  signable: boolean;
  pending: boolean;
  error: string | null;
  providerName: string;
  attestation: string;
  onSign: () => void;
}

export function AddendumPanel(props: AddendumPanelProps) {
  const { header, lines, confirmed, onConfirm, signable, pending, error, providerName, attestation, onSign } = props;
  return (
    <Panel aria-label={RESPOND_TEXT.previewTitle} className="flex flex-col gap-3.5 px-5 py-4.5">
      <div>
        <h2 className="m-0 mb-1 font-sans text-caption font-semibold text-tertiary">{RESPOND_TEXT.previewTitle}</h2>
        <div aria-live="polite">
          {lines.length > 0 ? (
            [header, ...lines].map((line) => (
              <p key={line} className="m-0 text-body-lg">
                {line}
              </p>
            ))
          ) : (
            <p className="m-0 text-body text-secondary">{RESPOND_TEXT.previewEmpty}</p>
          )}
        </div>
      </div>
      <label className="flex cursor-pointer items-center gap-3 text-body">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(event) => onConfirm(event.target.checked)}
          className="size-5 flex-none accent-label"
        />
        {attestation}
      </label>
      {error ? <InlineAlert tone="bad">{error}</InlineAlert> : null}
      <Button variant="primary" size="lg" className="w-full" disabled={!signable} pending={pending} onClick={onSign}>
        {RESPOND_TEXT.sign}
      </Button>
      <span className="text-center text-footnote text-tertiary">{RESPOND_TEXT.signedAs(providerName)}</span>
    </Panel>
  );
}
