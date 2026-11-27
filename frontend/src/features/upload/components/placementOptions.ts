import type { SelectOption } from "@/components/ui/Select";
import type { Place, Provider } from "@/lib/api/types";
import { UPLOAD_TEXT } from "../strings";

const words = UPLOAD_TEXT.plan;

export function providerOptions(providers: Provider[], blank: string): SelectOption[] {
  return [
    { value: "", label: blank, disabled: true },
    ...providers.map((provider) => ({ value: provider.id, label: words.providerOption(provider.name, provider.credential) })),
  ];
}

export function placeOptions(places: Place[], blank: string): SelectOption[] {
  return [{ value: "", label: blank, disabled: true }, ...places.map((place) => ({ value: place.code, label: words.placeOption(place.name, place.code) }))];
}
