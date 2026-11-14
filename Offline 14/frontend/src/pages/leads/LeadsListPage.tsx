import { useTranslation } from "react-i18next"
import { useState } from "react"
import { Plus, Search, UserPlus } from "lucide-react"
import { Link } from "react-router-dom"

import { EmptyState, GlassCard, GradientButton, PageWrapper } from "@/components/common"
import { ListSkeleton } from "@/components/contacts/PageSkeletons"
import { Pagination } from "@/components/contacts/Pagination"
import { LEAD_SOURCE_LABELS, LEAD_SOURCES, LEAD_STATUS_LABELS, LEAD_STATUSES } from "@/components/leads/constants"
import { LeadsTable } from "@/components/leads/LeadsTable"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useDebounce } from "@/hooks/useDebounce"
import { useLeads } from "@/hooks/useLeads"
import { getErrorMessage } from "@/services/api"
import type { LeadSource, LeadStatus } from "@/types"

const PAGE_SIZE = 20
const ALL = "all"

export default function LeadsListPage() {
  const { t } = useTranslation()
  const [search, setSearch] = useState("")
  const [status, setStatus] = useState<LeadStatus | undefined>(undefined)
  const [source, setSource] = useState<LeadSource | undefined>(undefined)
  const [page, setPage] = useState(1)
  const debouncedSearch = useDebounce(search.trim(), 300)

  const { data, isLoading, isError, error } = useLeads({
    search: debouncedSearch || undefined,
    status,
    source,
    page,
    page_size: PAGE_SIZE,
  })

  const hasFilters = debouncedSearch !== "" || status !== undefined || source !== undefined

  const newButton = (
    <GradientButton asChild>
      <Link to="/leads/new">
        <Plus /> {t("leads.new")}
      </Link>
    </GradientButton>
  )

  return (
    <PageWrapper title={t("nav.leads")} actions={newButton}>
      <GlassCard hoverable={false} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder={t("contacts.searchPlaceholder")}
            aria-label={t("leads.searchAria")}
            className="pl-8"
          />
        </div>
        <Select
          value={status ?? ALL}
          onValueChange={(v) => {
            setStatus(v === ALL ? undefined : (v as LeadStatus))
            setPage(1)
          }}
        >
          <SelectTrigger className="w-full sm:w-40" aria-label={t("leads.filterStatus")}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>{t("leads.allStatuses")}</SelectItem>
            {LEAD_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {LEAD_STATUS_LABELS[s]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={source ?? ALL}
          onValueChange={(v) => {
            setSource(v === ALL ? undefined : (v as LeadSource))
            setPage(1)
          }}
        >
          <SelectTrigger className="w-full sm:w-40" aria-label={t("leads.filterSource")}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>{t("leads.allSources")}</SelectItem>
            {LEAD_SOURCES.map((s) => (
              <SelectItem key={s} value={s}>
                {LEAD_SOURCE_LABELS[s]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </GlassCard>

      {isLoading ? (
        <ListSkeleton />
      ) : isError ? (
        <EmptyState title={t("leads.loadError")} description={getErrorMessage(error)} />
      ) : !data || data.items.length === 0 ? (
        hasFilters ? (
          <EmptyState icon={Search} title={t("leads.noMatches")} description={t("leads.noMatchesText")} />
        ) : (
          <EmptyState
            icon={UserPlus}
            title={t("leads.emptyTitle")}
            description={t("leads.emptyText")}
            action={newButton}
          />
        )
      ) : (
        <>
          <LeadsTable leads={data.items} />
          <Pagination page={data.page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
        </>
      )}
    </PageWrapper>
  )
}
