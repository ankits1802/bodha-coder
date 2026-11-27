import { StatusDot } from "@/components/ui/StatusDot";
import type { EmMix, EmMixProvider } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { CMS_SWATCH, FamilyChart, PROVIDER_SWATCH } from "./FamilyChart";
import { EM_MIX_TEXT } from "./strings";

function Legend({ year }: { year: string }) {
  return (
    <ul aria-label={EM_MIX_TEXT.legendLabel} className="m-0 flex list-none flex-wrap gap-x-4 gap-y-1 p-0 text-footnote text-secondary">
      <li className="inline-flex items-center gap-1.5">
        <span aria-hidden="true" className={`size-2.5 rounded-sm ${PROVIDER_SWATCH}`} />
        {EM_MIX_TEXT.provider}
      </li>
      <li className="inline-flex items-center gap-1.5">
        <span aria-hidden="true" className={`size-2.5 rounded-sm ${CMS_SWATCH}`} />
        {EM_MIX_TEXT.cms(year)}
      </li>
    </ul>
  );
}

function ProviderMix({ provider }: { provider: EmMixProvider }) {
  return (
    <section aria-label={provider.name} className="flex flex-col gap-3">
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h3 className="m-0 font-sans text-headline font-semibold tracking-headline">{provider.name}</h3>
        <span className="text-subhead text-secondary tabular-nums">{EM_MIX_TEXT.visits(formatCount(provider.visits), provider.visits)}</span>
        {provider.cms_specialty ? (
          <span className="text-subhead text-secondary">{EM_MIX_TEXT.specialty(provider.specialty ?? "", provider.cms_specialty)}</span>
        ) : (
          <StatusDot tone="neutral">{EM_MIX_TEXT.noSpecialty}</StatusDot>
        )}
      </header>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(17rem,1fr))] gap-3">
        {provider.families.map((family) => (
          <FamilyChart key={family.family} family={family} />
        ))}
      </div>
    </section>
  );
}

export function EmMixView({ mix }: { mix: EmMix }) {
  return (
    <div className="flex flex-col gap-5 px-4.5 pb-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Legend year={mix.benchmark.year} />
        <a href={mix.benchmark.source_url} className="text-footnote text-secondary underline underline-offset-2" rel="noreferrer" target="_blank">
          {EM_MIX_TEXT.source(mix.benchmark.dataset, mix.benchmark.year)}
        </a>
      </div>
      {mix.providers.map((provider) => (
        <ProviderMix key={provider.id} provider={provider} />
      ))}
    </div>
  );
}
