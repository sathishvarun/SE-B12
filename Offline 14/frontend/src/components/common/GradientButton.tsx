import type { ComponentProps } from "react"
import { motion } from "framer-motion"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type GradientButtonProps = ComponentProps<typeof Button>

/** Primary call-to-action: a rounded grape button with a soft "pressable" edge. */
export function GradientButton({ className, ...props }: GradientButtonProps) {
  return (
    <motion.div className="inline-flex" whileHover={{ y: -1 }} whileTap={{ y: 1 }}>
      <Button
        className={cn(
          "rounded-full bg-primary px-5 font-bold text-primary-foreground shadow-[0_3px_0_0_oklch(0.42_0.2_292)] hover:bg-primary/90 active:shadow-[0_1px_0_0_oklch(0.42_0.2_292)]",
          className,
        )}
        {...props}
      />
    </motion.div>
  )
}
