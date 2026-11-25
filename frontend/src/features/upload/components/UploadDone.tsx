import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { InlineAlert } from "@/components/ui/InlineAlert";
import type { UploadResult } from "@/lib/api/types";
import { UPLOAD_TEXT } from "../strings";

interface UploadDoneProps {
  result: UploadResult;
  onMore: () => void;
}

export function UploadDone({ result, onMore }: UploadDoneProps) {
  const words = UPLOAD_TEXT.done;
  return (
    <section className="flex flex-col gap-4">
      <InlineAlert tone="ok">{words.accepted(result.accepted.length)}</InlineAlert>
      {result.duplicates.length > 0 ? <InlineAlert tone="warn">{words.duplicates(result.duplicates.join(", "))}</InlineAlert> : null}
      <div className="flex flex-wrap gap-2.5">
        <ButtonLink href="/today" variant="primary">
          {words.today}
        </ButtonLink>
        <Button onClick={onMore}>{words.more}</Button>
      </div>
    </section>
  );
}
