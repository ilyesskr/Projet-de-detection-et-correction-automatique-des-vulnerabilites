import { PageHeader } from "@/components/layout/PageHeader";
import { IntegrationCard } from "@/components/integrations/IntegrationCard";
import { SyncControls } from "@/components/integrations/SyncControls";

import {
  useAnsibleHealth,
  useWazuhHealth,
} from "@/hooks/queries/useIntegrationHealth";
import { usePermissions } from "@/hooks/usePermissions";

export default function IntegrationsPage() {
  const { has } = usePermissions();
  const wazuhQuery = useWazuhHealth();
  const ansibleQuery = useAnsibleHealth();

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <PageHeader
        title="Integrations"
        description="Live health of the upstream systems the platform depends on."
      />

      <div className="grid gap-4 md:grid-cols-2">
        <IntegrationCard
          name="Wazuh"
          description="Source of truth for asset inventory and vulnerability detection."
          query={wazuhQuery}
        />
        <IntegrationCard
          name="Ansible AWX"
          description="Executes the approved remediation playbooks."
          query={ansibleQuery}
        />
      </div>

      {has("sync:run") && <SyncControls />}
    </div>
  );
}
