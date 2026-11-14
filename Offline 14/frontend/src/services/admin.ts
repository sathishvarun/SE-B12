import api from "@/services/api"
import type { AdminStats, AdminUser, AdminUserUpdate, Page, PaginationParams } from "@/types"

export interface AdminUsersParams extends PaginationParams {
  search?: string
}

export const adminService = {
  listUsers: async (params: AdminUsersParams): Promise<Page<AdminUser>> => {
    const { data } = await api.get<Page<AdminUser>>("/admin/users", {
      params: { ...params, search: params.search || undefined },
    })
    return data
  },

  updateUser: async (id: number, input: AdminUserUpdate): Promise<AdminUser> => {
    const { data } = await api.put<AdminUser>(`/admin/users/${id}`, input)
    return data
  },

  getStats: async (): Promise<AdminStats> => {
    const { data } = await api.get<AdminStats>("/admin/stats")
    return data
  },
}
