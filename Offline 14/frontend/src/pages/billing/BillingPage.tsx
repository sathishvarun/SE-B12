import i18n, { formatLocale } from "@/i18n"
import { useTranslation } from "react-i18next"
import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { CreditCard, Crown, Sparkles } from "lucide-react"
import { Link, useSearchParams } from "react-router-dom"
import { toast } from "sonner"

import { GlassCard, GradientButton, LoadingSpinner, PageWrapper } from "@/components/common"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useAuth } from "@/hooks/useAuth"
import { getErrorMessage } from "@/services/api"
import { billingService } from "@/services/billing"
import type { Subscription, SubscriptionStatus } from "@/types"

const SUBSCRIPTION_QUERY_KEY = ["billing", "subscription"] as const

// After returning from checkout, the webhook may arrive a few seconds later,
// so we re-fetch the subscription for a short while.
const POLL_INTERVAL_MS = 3000
const POLL_DURATION_MS = 20000

// Getters, so the labels always use the current language.
const STATUS_LABELS: Record<SubscriptionStatus, string> = {
  get active() { return i18n.t("billing.status.active") },
  get trialing() { return i18n.t("billing.status.trialing") },
  get past_due() { return i18n.t("billing.status.past_due") },
  get cancelled() { return i18n.t("billing.status.cancelled") },
}

function formatDate(value: string | null): string {
  if (!value) return "—"
  return new Date(value).toLocaleDateString(formatLocale(), { year: "numeric", month: "long", day: "numeric" })
}

function UsageBar({ label, used, limit }: { label: string; used: number; limit: number | null }) {
  const { t } = useTranslation()
  const nearLimit = limit !== null && used >= limit * 0.8
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">
          {used} / {limit === null ? t("billing.unlimited") : limit}
        </span>
      </div>
      <progress
        aria-label={t("billing.used", { label })}
        value={limit === null ? 0 : Math.min(used, limit)}
        max={limit ?? 1}
        className={
          "h-2 w-full appearance-none overflow-hidden rounded-full bg-muted " +
          "[&::-webkit-progress-bar]:bg-muted " +
          (nearLimit
            ? "[&::-moz-progress-bar]:bg-amber-500 [&::-webkit-progress-value]:bg-amber-500"
            : "[&::-moz-progress-bar]:bg-violet-600 [&::-webkit-progress-value]:bg-violet-600")
        }
      />
    </div>
  )
}

export default function BillingPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { user, refreshUser } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const checkoutSuccess = searchParams.get("checkout") === "success"
  // True for a short while after returning from checkout.
  const [isPollingWindow, setIsPollingWindow] = useState(checkoutSuccess)
  const [cancelOpen, setCancelOpen] = useState(false)

  const { data: subscription, isLoading, isError, error, refetch } = useQuery({
    queryKey: SUBSCRIPTION_QUERY_KEY,
    queryFn: billingService.getSubscription,
    refetchInterval: (query) => (isPollingWindow && query.state.data?.plan !== "pro" ? POLL_INTERVAL_MS : false),
  })

  useEffect(() => {
    if (!isPollingWindow) return
    const timer = window.setTimeout(() => setIsPollingWindow(false), POLL_DURATION_MS)
    return () => window.clearTimeout(timer)
  }, [isPollingWindow])

  // Show a toast once when coming back from a successful checkout, then clean the URL.
  useEffect(() => {
    if (checkoutSuccess) {
      toast.success(t("billing.checkoutSuccess"), { id: "checkout-success" })
      setSearchParams({}, { replace: true })
    }
  }, [checkoutSuccess, setSearchParams, t])

  // Keep the user's plan (shown in the top bar) in sync with the subscription.
  useEffect(() => {
    if (subscription && user && subscription.plan !== user.plan) {
      refreshUser().catch((err: unknown) => toast.error(getErrorMessage(err)))
    }
  }, [subscription, user, refreshUser])

  const checkout = useMutation({
    mutationFn: billingService.createCheckout,
    onSuccess: ({ checkout_url }) => {
      window.location.href = checkout_url
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const cancel = useMutation({
    mutationFn: billingService.cancel,
    onSuccess: (updated: Subscription) => {
      queryClient.setQueryData(SUBSCRIPTION_QUERY_KEY, updated)
      setCancelOpen(false)
      toast.success(t("billing.cancelled"))
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  if (isLoading) {
    return (
      <PageWrapper title={t("nav.billing")}>
        <LoadingSpinner fullPage label={t("billing.loading")} />
      </PageWrapper>
    )
  }

  if (isError || !subscription) {
    return (
      <PageWrapper title={t("nav.billing")}>
        <GlassCard hoverable={false} className="flex flex-col items-start gap-3">
          <p className="text-sm text-destructive">{getErrorMessage(error)}</p>
          <Button variant="outline" onClick={() => refetch()}>
            {t("common.tryAgain")}
          </Button>
        </GlassCard>
      </PageWrapper>
    )
  }

  const isPro = subscription.plan === "pro"
  const isCancelled = subscription.status === "cancelled"
  const isPolling = isPollingWindow && !isPro

  return (
    <PageWrapper title={t("nav.billing")}>
      <div className="grid gap-6 lg:grid-cols-3">
        <GlassCard hoverable={false} className="flex flex-col gap-5 lg:col-span-2">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-pink-100 p-3 text-pink-700">
                {isPro ? <Crown className="size-6" /> : <CreditCard className="size-6" />}
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t("billing.currentPlan")}</p>
                <h2 className="text-2xl font-bold">{isPro ? t("common.pro") : t("common.free")}</h2>
              </div>
            </div>
            <Badge variant={subscription.status === "past_due" || isCancelled ? "destructive" : "secondary"}>
              {STATUS_LABELS[subscription.status]}
            </Badge>
          </div>

          {isPolling && (
            <div className="flex items-center gap-2 rounded-lg bg-violet-50 p-3 text-sm text-violet-700">
              <LoadingSpinner />
              {t("billing.waiting")}
            </div>
          )}

          {isPro && (
            <p className="text-sm text-muted-foreground">
              {isCancelled ? t("billing.accessEnds") : t("billing.renews")}
              <span className="font-medium text-foreground">{formatDate(subscription.current_period_end)}</span>
            </p>
          )}

          <div className="flex flex-col gap-4">
            <UsageBar label={t("nav.contacts")} used={subscription.usage.contacts} limit={subscription.limits.max_contacts} />
            <UsageBar
              label={t("dashboard.openDeals")}
              used={subscription.usage.open_deals}
              limit={subscription.limits.max_open_deals}
            />
          </div>

          <div className="flex flex-wrap gap-3">
            {!isPro && (
              <GradientButton onClick={() => checkout.mutate()} disabled={checkout.isPending}>
                <Sparkles className="size-4" />
                {checkout.isPending ? t("billing.redirecting") : t("common.upgradeToPro")}
              </GradientButton>
            )}
            {isPro && !isCancelled && (
              <Button variant="destructive" onClick={() => setCancelOpen(true)}>
                {t("billing.cancelSubscription")}
              </Button>
            )}
            <Button variant="outline" asChild>
              <Link to="/pricing">{t("billing.comparePlans")}</Link>
            </Button>
          </div>
        </GlassCard>

        <GlassCard hoverable={false} className="flex flex-col gap-3">
          <h3 className="font-semibold">{isPro ? t("billing.onPro") : t("billing.whyUpgrade")}</h3>
          <ul className="flex flex-col gap-2 text-sm text-muted-foreground">
            <li>{t("billing.perkContacts")}</li>
            <li>{t("billing.perkDeals")}</li>
            <li>{t("billing.perkEverything")}</li>
          </ul>
          <p className="text-xs text-muted-foreground">{t("billing.securedBy")}</p>
        </GlassCard>
      </div>

      <Dialog open={cancelOpen} onOpenChange={setCancelOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("billing.cancelTitle")}</DialogTitle>
            <DialogDescription>
              {t("billing.cancelText")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">{t("billing.keepPro")}</Button>
            </DialogClose>
            <Button variant="destructive" onClick={() => cancel.mutate()} disabled={cancel.isPending}>
              {cancel.isPending ? t("billing.cancelling") : t("billing.yesCancel")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageWrapper>
  )
}
