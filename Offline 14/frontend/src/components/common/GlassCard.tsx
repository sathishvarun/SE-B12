import { motion, type HTMLMotionProps } from "framer-motion"

import { cn } from "@/lib/utils"

interface GlassCardProps extends HTMLMotionProps<"div"> {
  /** Lift the card slightly on hover (default: true). */
  hoverable?: boolean
}

/** Soft, rounded white card with a gentle shadow. Use for all card containers. */
export function GlassCard({ className, hoverable = true, children, ...props }: GlassCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={hoverable ? { y: -3 } : undefined}
      transition={{ duration: 0.25 }}
      className={cn(
        "rounded-3xl border border-border/70 bg-card p-6 shadow-[0_2px_0_0_oklch(0.92_0.018_295),0_8px_24px_-12px_oklch(0.55_0.21_292/0.18)] transition-shadow",
        hoverable && "hover:shadow-[0_2px_0_0_oklch(0.92_0.018_295),0_14px_32px_-12px_oklch(0.55_0.21_292/0.28)]",
        className,
      )}
      {...props}
    >
      {children}
    </motion.div>
  )
}
