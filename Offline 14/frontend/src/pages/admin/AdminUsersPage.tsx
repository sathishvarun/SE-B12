import { formatLocale } from "@/i18n"
import { useTranslation } from "react-i18next"
import { useEffect, useState } from "react"
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Search, Users } from "lucide-react"
import { toast } from "sonner"

import { EmptyState, GlassCard, LoadingSpinner, PageWrapper } from "@/components/common"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAuth } from "@/hooks/useAuth"
import { getErrorMessage } from "@/services/api"
import { adminService } from "@/services/admin"
import type { AdminUser, AdminUserUpdate } from "@/types"

const PAGE_SIZE = 20

export default function AdminUsersPage() {
  const { t } = useTranslation()
  const { user: me } = useAuth()
  const queryClient = useQueryClient()
  const [searchInput, setSearchInput] = useState("")
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)

  // Wait until the admin stops typing before searching.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 300)
    return () => window.clearTimeout(timer)
  }, [searchInput])

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["admin", "users", { search, page }],
    queryFn: () => adminService.listUsers({ search, page, page_size: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  })

  const update = useMutation({
    mutationFn: ({ id, input }: { id: number; input: AdminUserUpdate }) => adminService.updateUser(id, input),
    onSuccess: (updated: AdminUser) => {
      toast.success(t("admin.updated", { email: updated.email }))
      void queryClient.invalidateQueries({ queryKey: ["admin"] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1

  return (
    <PageWrapper title={t("admin.usersTitle")}>
      <GlassCard hoverable={false} className="flex flex-col gap-4">
        <div className="relative max-w-sm">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={t("admin.searchPlaceholder")}
            aria-label={t("admin.searchAria")}
            className="pl-9"
          />
        </div>

        {isLoading && <LoadingSpinner fullPage label={t("admin.loadingUsers")} />}

        {isError && (
          <div className="flex flex-col items-start gap-3">
            <p className="text-sm text-destructive">{getErrorMessage(error)}</p>
            <Button variant="outline" onClick={() => refetch()}>
              {t("common.tryAgain")}
            </Button>
          </div>
        )}

        {data && data.items.length === 0 && (
          <EmptyState icon={Users} title={t("admin.noUsers")} description={t("admin.noUsersText")} />
        )}

        {data && data.items.length > 0 && (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("admin.user")}</TableHead>
                  <TableHead>{t("admin.plan")}</TableHead>
                  <TableHead className="hidden md:table-cell">{t("admin.joined")}</TableHead>
                  <TableHead className="text-center">{t("admin.active")}</TableHead>
                  <TableHead className="text-center">{t("nav.admin")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((row) => {
                  const isSelf = row.id === me?.id
                  const busy = update.isPending && update.variables?.id === row.id
                  return (
                    <TableRow key={row.id}>
                      <TableCell>
                        <div className="flex flex-col">
                          <span className="font-medium">
                            {row.full_name ?? "—"}
                            {isSelf && <span className="ml-1 text-xs text-muted-foreground">{t("admin.you")}</span>}
                          </span>
                          <span className="text-xs text-muted-foreground">{row.email}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={row.plan === "pro" ? "default" : "secondary"}>
                          {row.plan === "pro" ? t("common.pro") : t("common.free")}
                        </Badge>
                      </TableCell>
                      <TableCell className="hidden md:table-cell">
                        {new Date(row.created_at).toLocaleDateString(formatLocale())}
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-center">
                          <Checkbox
                            checked={row.is_active}
                            disabled={isSelf || busy}
                            aria-label={t("admin.activeAria", { email: row.email })}
                            onCheckedChange={(checked) =>
                              update.mutate({ id: row.id, input: { is_active: checked === true } })
                            }
                          />
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-center">
                          <Checkbox
                            checked={row.is_admin}
                            disabled={isSelf || busy}
                            aria-label={t("admin.adminAria", { email: row.email })}
                            onCheckedChange={(checked) =>
                              update.mutate({ id: row.id, input: { is_admin: checked === true } })
                            }
                          />
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>

            <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
              <span>
                {t("admin.userCount", { count: data.total })} · {t("common.pageOf", { page: data.page, total: totalPages })}
                {isFetching && t("admin.refreshing")}
              </span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  {t("common.previous")}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  {t("common.next")}
                </Button>
              </div>
            </div>
          </>
        )}
      </GlassCard>
    </PageWrapper>
  )
}
