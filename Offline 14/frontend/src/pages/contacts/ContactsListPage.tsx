import { useTranslation } from "react-i18next"
import { useState } from "react"
import { Plus, Search, Users } from "lucide-react"
import { Link } from "react-router-dom"

import { EmptyState, GlassCard, GradientButton, PageWrapper } from "@/components/common"
import { ContactsTable } from "@/components/contacts/ContactsTable"
import { ListSkeleton } from "@/components/contacts/PageSkeletons"
import { Pagination } from "@/components/contacts/Pagination"
import { TagFilter } from "@/components/contacts/TagFilter"
import { Input } from "@/components/ui/input"
import { useContacts, useTags } from "@/hooks/useContacts"
import { useDebounce } from "@/hooks/useDebounce"
import { getErrorMessage } from "@/services/api"

const PAGE_SIZE = 20

export default function ContactsListPage() {
  const { t } = useTranslation()
  const [search, setSearch] = useState("")
  const [tagId, setTagId] = useState<number | undefined>(undefined)
  const [page, setPage] = useState(1)
  const debouncedSearch = useDebounce(search.trim(), 300)

  const { data: tags = [] } = useTags()
  const { data, isLoading, isError, error } = useContacts({
    search: debouncedSearch || undefined,
    tag_id: tagId,
    page,
    page_size: PAGE_SIZE,
  })

  const hasFilters = debouncedSearch !== "" || tagId !== undefined

  const newButton = (
    <GradientButton asChild>
      <Link to="/contacts/new">
        <Plus /> {t("contacts.new")}
      </Link>
    </GradientButton>
  )

  return (
    <PageWrapper title={t("nav.contacts")} actions={newButton}>
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
            aria-label={t("contacts.searchAria")}
            className="pl-8"
          />
        </div>
        <TagFilter
          tags={tags}
          value={tagId}
          onChange={(id) => {
            setTagId(id)
            setPage(1)
          }}
        />
      </GlassCard>

      {isLoading ? (
        <ListSkeleton />
      ) : isError ? (
        <EmptyState title={t("contacts.loadError")} description={getErrorMessage(error)} />
      ) : !data || data.items.length === 0 ? (
        hasFilters ? (
          <EmptyState icon={Search} title={t("contacts.noMatches")} description={t("contacts.noMatchesText")} />
        ) : (
          <EmptyState
            icon={Users}
            title={t("contacts.emptyTitle")}
            description={t("contacts.emptyText")}
            action={newButton}
          />
        )
      ) : (
        <>
          <ContactsTable contacts={data.items} />
          <Pagination page={data.page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
        </>
      )}
    </PageWrapper>
  )
}
