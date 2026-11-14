import i18n from "@/i18n"
import { useCallback } from "react"
import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import { dashboardKeys } from "@/hooks/useDashboard"
import { getErrorMessage } from "@/services/api"
import { dealsService, type DealListParams } from "@/services/deals"
import { DEAL_STAGES, type DealBoard, type DealInput, type DealStage } from "@/types"

export const dealKeys = {
  all: ["deals"] as const,
  board: ["deals", "board"] as const,
  list: (params: DealListParams) => ["deals", "list", params] as const,
  detail: (id: number) => ["deals", "detail", id] as const,
}

/** Deals feed the dashboard and contact pages too, so refresh all of them. */
function invalidateDealData(queryClient: QueryClient) {
  void queryClient.invalidateQueries({ queryKey: dealKeys.all })
  void queryClient.invalidateQueries({ queryKey: dashboardKeys.all })
  void queryClient.invalidateQueries({ queryKey: ["contacts"] })
}

/** Make sure every stage has an array, even if the API leaves one out. */
function normalizeBoard(board: DealBoard): DealBoard {
  return Object.fromEntries(DEAL_STAGES.map((stage) => [stage, board[stage] ?? []])) as DealBoard
}

export function useDealBoard() {
  return useQuery({ queryKey: dealKeys.board, queryFn: dealsService.board, select: normalizeBoard })
}

export function useDeals(params: DealListParams = {}) {
  return useQuery({ queryKey: dealKeys.list(params), queryFn: () => dealsService.list(params) })
}

export function useDeal(id: number) {
  return useQuery({
    queryKey: dealKeys.detail(id),
    queryFn: () => dealsService.get(id),
    enabled: Number.isFinite(id) && id > 0,
  })
}

export function useCreateDeal() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: DealInput) => dealsService.create(input),
    onSuccess: () => {
      toast.success(i18n.t("deals.toast.created"))
      invalidateDealData(queryClient)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}

export function useUpdateDeal(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: DealInput) => dealsService.update(id, input),
    onSuccess: () => {
      toast.success(i18n.t("deals.toast.updated"))
      invalidateDealData(queryClient)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}

export function useDeleteDeal() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => dealsService.remove(id),
    onSuccess: (_data, id) => {
      toast.success(i18n.t("deals.toast.deleted"))
      queryClient.removeQueries({ queryKey: dealKeys.detail(id) })
      invalidateDealData(queryClient)
      void queryClient.invalidateQueries({ queryKey: ["tasks"] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })
}

interface MoveVariables {
  id: number
  stage: DealStage
  position: number
  /** Board as it was before an optimistic update, used for rollback. */
  previousBoard?: DealBoard
}

/**
 * Move a deal to a stage/position (PATCH /deals/{id}/stage).
 * Pass `nextBoard` to optimistically update the board cache right away;
 * it is rolled back (with a toast) if the request fails.
 */
export function useMoveDeal() {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: ({ id, stage, position }: MoveVariables) => dealsService.moveStage(id, { stage, position }),
    onError: (err, variables) => {
      if (variables.previousBoard) {
        queryClient.setQueryData(dealKeys.board, variables.previousBoard)
      }
      toast.error(getErrorMessage(err))
    },
    onSettled: () => invalidateDealData(queryClient),
  })

  const { mutate } = mutation
  const move = useCallback(
    (id: number, stage: DealStage, position: number, nextBoard?: DealBoard) => {
      let previousBoard: DealBoard | undefined
      if (nextBoard) {
        // Stop any in-flight board fetch from overwriting the optimistic state.
        void queryClient.cancelQueries({ queryKey: dealKeys.board }, { revert: false, silent: true })
        previousBoard = queryClient.getQueryData<DealBoard>(dealKeys.board)
        queryClient.setQueryData(dealKeys.board, nextBoard)
      }
      mutate({ id, stage, position, previousBoard })
    },
    [mutate, queryClient],
  )

  return { move, isPending: mutation.isPending }
}
