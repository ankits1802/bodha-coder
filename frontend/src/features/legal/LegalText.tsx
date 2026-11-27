import { Fragment } from "react";
import { splitPlaceholders } from "./placeholders";

export function LegalText({ text }: { text: string }) {
  return (
    <>
      {splitPlaceholders(text).map((part, index) =>
        part.placeholder ? (
          <mark key={index} className="box-decoration-clone rounded-chip bg-warn-surface px-0.5 text-label">
            {part.text}
          </mark>
        ) : (
          <Fragment key={index}>{part.text}</Fragment>
        ),
      )}
    </>
  );
}
