import { apiClient } from "@/lib/apiClient";
import type { Asset, Page, Vulnerability } from "@/api/types";

export interface ListAssetsParams {
  limit?: number;
  offset?: number;
  search?: string;
}

export async function listAssets(
  params: ListAssetsParams = {},
): Promise<Page<Asset>> {
  const r = await apiClient.get<Page<Asset>>("/assets", { params });
  return r.data;
}

export async function getAsset(id: string): Promise<Asset> {
  const r = await apiClient.get<Asset>(`/assets/${id}`);
  return r.data;
}

export interface ListAssetVulnsParams {
  limit?: number;
  offset?: number;
}

export async function listAssetVulnerabilities(
  assetId: string,
  params: ListAssetVulnsParams = {},
): Promise<Page<Vulnerability>> {
  const r = await apiClient.get<Page<Vulnerability>>(
    `/assets/${assetId}/vulnerabilities`,
    { params },
  );
  return r.data;
}
