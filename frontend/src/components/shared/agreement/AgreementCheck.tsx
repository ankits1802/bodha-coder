import { useId, type ReactNode } from "react";
import type { SignUpOptions } from "@/lib/api/types";
import { AGREEMENT_TEXT } from "./strings";

type DocumentKey = keyof typeof AGREEMENT_TEXT.documents;

interface AgreementDocument {
  key: DocumentKey;
  href: string;
}

interface AgreementCheckProps {
  options: SignUpOptions;
  checked: boolean;
  error: string | null | undefined;
  onChange: (checked: boolean) => void;
  onBlur?: () => void;
}

const LINK = "font-medium text-label underline underline-offset-2";
const LIST = new Intl.ListFormat("en-US", { style: "long", type: "conjunction" });

export function agreementDocuments(options: SignUpOptions): AgreementDocument[] {
  const listed: [DocumentKey, string | null][] = [
    ["terms", options.terms_url],
    ["baa", options.baa_url],
    ["privacy", options.privacy_url],
  ];
  return listed.flatMap(([key, href]) => (href ? [{ key, href }] : []));
}

function documentNames(documents: AgreementDocument[]): string[] {
  return documents.map((document) => AGREEMENT_TEXT.documents[document.key]);
}

function documentLinks(documents: AgreementDocument[]): ReactNode[] {
  const parts = LIST.formatToParts(documentNames(documents));
  const nodes: ReactNode[] = [];
  let next = 0;
  for (const [position, part] of parts.entries()) {
    const document = part.type === "element" ? documents[next++] : undefined;
    nodes.push(
      document ? (
        <a key={document.key} href={document.href} target="_blank" rel="noopener noreferrer" className={LINK}>
          {part.value}
        </a>
      ) : (
        <span key={`literal-${position}`}>{part.value}</span>
      ),
    );
  }
  return nodes;
}

function leadText(options: SignUpOptions, documents: AgreementDocument[]): string {
  if (!options.test_data_only) return AGREEMENT_TEXT.agreeTo;
  return documents.length > 0 ? AGREEMENT_TEXT.testDataAndAgree : AGREEMENT_TEXT.testDataOnly;
}

function spokenName(options: SignUpOptions, documents: AgreementDocument[]): string {
  const lead = leadText(options, documents);
  return documents.length > 0 ? `${lead} ${LIST.format(documentNames(documents))}` : lead;
}

export function AgreementCheck({ options, checked, error, onChange, onBlur }: AgreementCheckProps) {
  const id = useId();
  const documents = agreementDocuments(options);
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-start gap-3">
        <input
          id={id}
          type="checkbox"
          checked={checked}
          aria-label={spokenName(options, documents)}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : undefined}
          onChange={(event) => onChange(event.target.checked)}
          onBlur={onBlur}
          className="mt-0.5 size-4.5 flex-none accent-label"
        />
        <label htmlFor={id} className="text-body text-label">
          {leadText(options, documents)}
          {documents.length > 0 ? " " : null}
          {documentLinks(documents)}
        </label>
      </div>
      {error ? (
        <span id={`${id}-error`} className="text-footnote text-bad-text">
          {error}
        </span>
      ) : null}
    </div>
  );
}
