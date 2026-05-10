import { apiClient } from "@/lib/apiClient";
import type {
  Asset,
  Page,
  Role,
  User,
  UserCreate,
  UserUpdate,
} from "@/api/types";

export interface ListUsersParams {
  limit?: number;
  offset?: number;
  is_active?: boolean;
}

export async function listUsers(
  params: ListUsersParams = {},
): Promise<Page<User>> {
  const r = await apiClient.get<Page<User>>("/users", { params });
  return r.data;
}

export async function getUser(id: string): Promise<User> {
  const r = await apiClient.get<User>(`/users/${id}`);
  return r.data;
}

export async function createUser(body: UserCreate): Promise<User> {
  const r = await apiClient.post<User>("/users", body);
  return r.data;
}

export async function updateUser(
  id: string,
  body: UserUpdate,
): Promise<User> {
  const r = await apiClient.patch<User>(`/users/${id}`, body);
  return r.data;
}

export async function deleteUser(id: string): Promise<void> {
  await apiClient.delete(`/users/${id}`);
}

export async function listRoles(): Promise<Role[]> {
  const r = await apiClient.get<Role[]>("/roles");
  return r.data;
}

export async function getUserAssetScope(userId: string): Promise<Asset[]> {
  const r = await apiClient.get<Asset[]>(`/users/${userId}/asset-scopes`);
  return r.data;
}

export async function grantUserAssetScope(
  userId: string,
  assetId: string,
): Promise<void> {
  await apiClient.post(`/users/${userId}/asset-scopes`, {
    asset_id: assetId,
  });
}

export async function revokeUserAssetScope(
  userId: string,
  assetId: string,
): Promise<void> {
  await apiClient.delete(`/users/${userId}/asset-scopes/${assetId}`);
}
