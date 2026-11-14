import { GlassCard } from "@/components/common"
import { Skeleton } from "@/components/ui/skeleton"

/** Placeholder rows shown while a list is loading. */
export function ListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <GlassCard hoverable={false} className="flex flex-col gap-3" aria-busy="true">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </GlassCard>
  )
}

/** Placeholder layout shown while a detail page is loading. */
export function DetailSkeleton() {
  return (
    <div className="grid gap-6 lg:grid-cols-3" aria-busy="true">
      <GlassCard hoverable={false} className="flex flex-col gap-3">
        <Skeleton className="h-6 w-2/3" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </GlassCard>
      <div className="flex flex-col gap-6 lg:col-span-2">
        <GlassCard hoverable={false} className="flex flex-col gap-3">
          <Skeleton className="h-5 w-1/4" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </GlassCard>
        <GlassCard hoverable={false} className="flex flex-col gap-3">
          <Skeleton className="h-5 w-1/4" />
          <Skeleton className="h-10 w-full" />
        </GlassCard>
      </div>
    </div>
  )
}

/** Placeholder for an edit form. */
export function FormSkeleton() {
  return (
    <GlassCard hoverable={false} className="flex flex-col gap-4" aria-busy="true">
      {Array.from({ length: 4 }, (_, i) => (
        <Skeleton key={i} className="h-9 w-full" />
      ))}
    </GlassCard>
  )
}
