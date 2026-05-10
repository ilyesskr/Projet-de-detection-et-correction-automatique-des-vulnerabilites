import { keepPreviousData, useQuery } from "@tanstack/react-query";

import {
  listAssets,
  type ListAssetsParams,
  listAssetVulnerabilities,
  type ListAssetVulnsParams,
  getAsset,
} from "@/api/assets";

export function useAssets(params: ListAssetsParams) {
  return useQuery({
    queryKey: ["assets", "list", params],
    queryFn: () => listAssets(params),
    // Pagination + search shouldn't blank the table on each keystroke.
    placeholderData: keepPreviousData,
  });
}

export function useAsset(id: string | undefined) {
  return useQuery({
    queryKey: ["assets", "detail", id],
    queryFn: () => getAsset(id!),
    enabled: !!id,
  });
}

export function useAssetVulnerabilities(
  assetId: string | undefined,
  params: ListAssetVulnsParams = {},
) {
  return useQuery({
    queryKey: ["assets", "vulnerabilities", assetId, params],
    queryFn: () => listAssetVulnerabilities(assetId!, params),
    enabled: !!assetId,
    placeholderData: keepPreviousData,
  });
}
