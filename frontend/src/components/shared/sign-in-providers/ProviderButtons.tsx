import { buttonClasses } from "@/components/ui/buttonStyles";
import { providerStartPath } from "@/lib/api/auth";
import type { IdentityProviderName } from "@/lib/api/types";
import { SHARED_TEXT } from "../strings";
import { ProviderMark } from "./ProviderMarks";

const words = SHARED_TEXT.identityProviders;

export function providerName(provider: IdentityProviderName): string {
  return words.names[provider];
}

export function ProviderButtons({ providers }: { providers: readonly IdentityProviderName[] }) {
  if (providers.length === 0) return null;
  return (
    <div role="group" aria-label={words.label} className="flex flex-col gap-2.5">
      {providers.map((provider) => (
        <a key={provider} href={providerStartPath(provider)} className={buttonClasses("secondary", "lg", "w-full")}>
          <ProviderMark provider={provider} />
          {words.continueWith(providerName(provider))}
        </a>
      ))}
    </div>
  );
}
