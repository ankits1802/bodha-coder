"use client";

import { AreaGuard } from "@/components/shared/AreaGuard";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import type { Place, Provider } from "@/lib/api/types";
import { getPlaces, getProviders } from "@/lib/api/uploads";
import { canUse } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { UploadWorkspace } from "./components/UploadWorkspace";
import { UPLOAD_TEXT } from "./strings";

interface UploadReferences {
  providers: Provider[];
  places: Place[];
}

async function loadReferences(): Promise<UploadReferences> {
  const [providers, places] = await Promise.all([getProviders(), getPlaces()]);
  return { providers: providers.filter((provider) => provider.active), places };
}

const REMOTE_TEXT = { loading: UPLOAD_TEXT.loading, empty: UPLOAD_TEXT.noProviders, retry: UPLOAD_TEXT.retry };

function UploadContent() {
  const { user } = useSession();
  const references = useRemote("upload:references", loadReferences);
  const setupLink = canUse(user?.role, "setup") ? (
    <ButtonLink href="/setup" size="sm">
      {UPLOAD_TEXT.openSetup}
    </ButtonLink>
  ) : null;
  return (
    <RemoteView
      state={references.state}
      text={REMOTE_TEXT}
      isEmpty={(data) => data.providers.length === 0}
      emptyAction={setupLink}
      onRetry={references.reload}
    >
      {(data) => <UploadWorkspace providers={data.providers} places={data.places} />}
    </RemoteView>
  );
}

export function UploadScreen() {
  return (
    <>
      <PageHeader title={UPLOAD_TEXT.title} />
      <AreaGuard area="upload">
        <UploadContent />
      </AreaGuard>
    </>
  );
}
