"use client";

import { useState } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { useUsageTask } from "@/hooks/useUsageTask";
import { getPayers } from "@/lib/api/notes";
import type { PayerOption, Place, Provider } from "@/lib/api/types";
import { getPlaces, getProviders } from "@/lib/api/uploads";
import { setupSectionPath } from "@/lib/paths";
import { canUse } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { RecentUploads } from "./components/RecentUploads";
import { UploadWorkspace } from "./components/UploadWorkspace";
import { UPLOAD_TEXT } from "./strings";

interface UploadReferences {
  providers: Provider[];
  places: Place[];
  payers: PayerOption[];
}

async function loadReferences(): Promise<UploadReferences> {
  const [providers, places, payers] = await Promise.all([getProviders(), getPlaces(), getPayers()]);
  return { providers: providers.filter((provider) => provider.active), places, payers };
}

const REMOTE_TEXT = { loading: UPLOAD_TEXT.loading, empty: UPLOAD_TEXT.noProviders, retry: UPLOAD_TEXT.retry };

function UploadContent() {
  const { user } = useSession();
  const references = useRemote("upload:references", loadReferences);
  const [uploads, setUploads] = useState(0);
  const usage = useUsageTask("upload");
  const setupLink = canUse(user?.role, "setup") ? (
    <ButtonLink href={setupSectionPath("providers")} size="sm">
      {UPLOAD_TEXT.openSetup}
    </ButtonLink>
  ) : null;
  return (
    <>
      <RemoteView
        state={references.state}
        text={REMOTE_TEXT}
        isEmpty={(data) => data.providers.length === 0}
        emptyAction={setupLink}
        onRetry={references.reload}
      >
        {(data) => (
          <UploadWorkspace
            references={data}
            onUploaded={() => {
              usage.complete();
              setUploads((count) => count + 1);
            }}
          />
        )}
      </RemoteView>
      <RecentUploads refresh={uploads} />
    </>
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
