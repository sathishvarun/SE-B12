import api from "@/services/api"
import type { Deal, DealBoard, DealDetail, DealInput, DealStage, MoveDealInput, Page, PaginationParams } from "@/types"

export interface DealListParams extends PaginationParams {
  stage?: DealStage
  contact_id?: number
}

/** Thin wrappers around the /deals endpoints. */
export const dealsService = {
  async list(params: DealListParams = {}): Promise<Page<Deal>> {
    const { data } = await api.get<Page<Deal>>("/deals", { params })
    return data
  },

  async board(): Promise<DealBoard> {
    const { data } = await api.get<DealBoard>("/deals/board")
    return data
  },

  async get(id: number): Promise<DealDetail> {
    const { data } = await api.get<DealDetail>(`/deals/${id}`)
    return data
  },

  async create(input: DealInput): Promise<Deal> {
    const { data } = await api.post<Deal>("/deals", input)
    return data
  },

  async update(id: number, input: DealInput): Promise<Deal> {
    const { data } = await api.put<Deal>(`/deals/${id}`, input)
    return data
  },

  async moveStage(id: number, input: MoveDealInput): Promise<Deal> {
    const { data } = await api.patch<Deal>(`/deals/${id}/stage`, input)
    return data
  },

  async remove(id: number): Promise<void> {
    await api.delete(`/deals/${id}`)
  },
}
