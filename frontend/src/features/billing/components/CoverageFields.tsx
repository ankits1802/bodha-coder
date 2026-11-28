import { SegmentedControl } from "@/components/ui/SegmentedControl";
import type { Relationship } from "@/lib/api/types";
import { RELATIONSHIPS, SELF, type DetailsChange, type DetailsDraft, type DetailsErrors } from "../claimDetailsModel";
import { CLAIM_DETAILS_TEXT } from "../strings";
import { DetailInput } from "./DetailInput";

interface CoverageFieldsProps {
  draft: DetailsDraft;
  errors: DetailsErrors;
  onChange: DetailsChange;
}

export function CoverageFields({ draft, errors, onChange }: CoverageFieldsProps) {
  const words = CLAIM_DETAILS_TEXT;
  return (
    <>
      <div className="flex flex-col gap-1.5 sm:col-span-2">
        <span aria-hidden="true" className="text-subhead font-medium text-label">
          {words.relationship}
        </span>
        <SegmentedControl<Relationship>
          label={words.relationship}
          value={draft.relationship}
          segments={RELATIONSHIPS.map((value) => ({ value, label: words.relationships[value] }))}
          onChange={(relationship) => onChange({ relationship })}
        />
      </div>
      <DetailInput
        label={words.memberId}
        value={draft.member_id}
        maxLength={80}
        error={errors.member_id}
        onChange={(member_id) => onChange({ member_id })}
      />
      <DetailInput
        label={words.groupNumber}
        value={draft.group_number}
        maxLength={50}
        optional
        onChange={(group_number) => onChange({ group_number })}
      />
      {draft.relationship === SELF ? null : (
        <>
          <DetailInput
            label={words.subscriberLast}
            value={draft.subscriber_last}
            maxLength={60}
            error={errors.subscriber_last}
            onChange={(subscriber_last) => onChange({ subscriber_last })}
          />
          <DetailInput
            label={words.subscriberFirst}
            value={draft.subscriber_first}
            maxLength={35}
            error={errors.subscriber_first}
            onChange={(subscriber_first) => onChange({ subscriber_first })}
          />
        </>
      )}
    </>
  );
}
