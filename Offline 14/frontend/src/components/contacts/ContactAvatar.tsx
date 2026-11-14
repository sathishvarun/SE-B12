import { cn } from "@/lib/utils"

/** Friendly pastel colours; each contact always gets the same one (based on id). */
const AVATAR_COLORS = [
  "bg-emerald-100 text-emerald-700",
  "bg-orange-100 text-orange-700",
  "bg-sky-100 text-sky-700",
  "bg-amber-100 text-amber-700",
  "bg-pink-100 text-pink-700",
  "bg-violet-100 text-violet-700",
  "bg-teal-100 text-teal-700",
]

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("")
}

interface ContactAvatarProps {
  id: number
  name: string
  className?: string
}

/** Round initials badge in a colour picked from the contact's id. */
export function ContactAvatar({ id, name, className }: ContactAvatarProps) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-extrabold",
        AVATAR_COLORS[id % AVATAR_COLORS.length],
        className,
      )}
    >
      {initials(name)}
    </span>
  )
}
