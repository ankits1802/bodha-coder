import Link from "next/link";
import { Chevron } from "@/components/ui/Chevron";
import type { ProviderDay } from "@/lib/api/types";
import { formatCalendarDay } from "@/lib/format";
import { dayFacts, noteHref } from "./dayFacts";
import { DayFlags } from "./DayBannerView";
import { DAY_TEXT } from "./strings";

function DayRow({ day }: { day: ProviderDay }) {
  const first = day.notes[0];
  const title = DAY_TEXT.dayTitle(day.provider.name, formatCalendarDay(day.service_date, "long"));
  const content = (
    <>
      <span className="flex min-w-0 flex-1 basis-56 flex-col gap-0.5">
        <span className="truncate text-body-lg font-semibold">{title}</span>
        <span className="text-subhead text-secondary tabular-nums">{dayFacts(day).join(" · ")}</span>
      </span>
      <span className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <DayFlags flags={day.flags} />
      </span>
    </>
  );
  return (
    <li>
      {first ? (
        <Link href={noteHref(first.id)} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4.5 py-3.5 hover:bg-row-hover">
          {content}
          <Chevron />
        </Link>
      ) : (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4.5 py-3.5">{content}</div>
      )}
    </li>
  );
}

export function DayChecksList({ days }: { days: ProviderDay[] }) {
  return (
    <ul aria-label={DAY_TEXT.listLabel} className="m-0 list-none divide-y divide-hairline p-0">
      {days.map((day) => (
        <DayRow key={`${day.provider.id}:${day.service_date}`} day={day} />
      ))}
    </ul>
  );
}
