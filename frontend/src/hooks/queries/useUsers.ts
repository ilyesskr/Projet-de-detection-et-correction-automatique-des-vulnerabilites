import { keepPreviousData, useQuery } from "@tanstack/react-query";

import {
  getUser,
  getUserAssetScope,
  listRoles,
  listUsers,
  type ListUsersParams,
} from "@/api/users";

export function useUsers(params: ListUsersParams) {
  return useQuery({
    queryKey: ["users", "list", params],
    queryFn: () => listUsers(params),
    placeholderData: keepPreviousData,
  });
}

export function useUser(id: string | undefined) {
  return useQuery({
    queryKey: ["users", "detail", id],
    queryFn: () => getUser(id!),
    enabled: !!id,
  });
}

export function useRoles() {
  return useQuery({
    queryKey: ["roles"],
    queryFn: listRoles,
    // Roles change rarely; let them stay fresh for the session.
    staleTime: 5 * 60_000,
  });
}

export function useUserAssetScope(userId: string | undefined) {
  return useQuery({
    queryKey: ["users", "asset-scope", userId],
    queryFn: () => getUserAssetScope(userId!),
    enabled: !!userId,
  });
}
