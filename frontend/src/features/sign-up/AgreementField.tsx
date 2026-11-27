import { useId, type ReactNode } from "react";
import type { SignUpOptions } from "@/lib/api/types";
import { SIGN_UP_TEXT } from "./strings";
import type { DraftForm } from "./useSignUpDraft";

type DocumentKey = keyof typeof SIGN_UP_TEXT.documents;

interface AgreementDocument {
  key: DocumentKey;
  href: string;
}

const LINK = "font-medium text-label underline underline-offset-2";

export function agreementDocuments(options: SignUpOptions): AgreementDocument[] {
  const listed: [DocumentKey, string | null][] = [
    ["terms", options.terms_url],
    ["baa", options.baa_url],
    ["privacy", options.privacy_url],
  ];
  return listed.flatMap(([key, href]) => (href ? [{ key, href }] : []));
}

function documentLinks(documents: AgreementDocument[]): ReactNode[] {
  const names = documents.map((document) => SIGN_UP_TEXT.documents[document.key]);
  const parts = new Intl.ListFormat("en-US", { style: "long", type: "conjunction" }).formatToParts(names);
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
  if (!options.test_data_only) return SIGN_UP_TEXT.agreeTo;
  return documents.length > 0 ? SIGN_UP_TEXT.testDataAndAgree : SIGN_UP_TEXT.testDataOnly;
}

export function AgreementField({ form, options }: { form: DraftForm; options: SignUpOptions }) {
  const id = useId();
  const error = form.errors.agreed;
  const documents = agreementDocuments(options);
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-start gap-3">
        <input
          id={id}
          type="checkbox"
          checked={form.draft.agreed}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : undefined}
          onChange={(event) => form.change("agreed", event.target.checked)}
          onBlur={() => form.touch("agreed")}
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
