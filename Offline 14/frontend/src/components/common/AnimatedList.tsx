import { Children, type ReactNode } from "react"
import { motion, type Variants } from "framer-motion"

import { cn } from "@/lib/utils"

interface AnimatedListProps {
  children: ReactNode
  className?: string
}

const container: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
}

const item: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
}

/** Renders children with a staggered fade-in. Give each child a stable `key`. */
export function AnimatedList({ children, className }: AnimatedListProps) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={container}
      className={cn("flex flex-col gap-3", className)}
    >
      {Children.map(children, (child) => (
        <motion.div variants={item}>{child}</motion.div>
      ))}
    </motion.div>
  )
}
