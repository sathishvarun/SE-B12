/** Soft pastel background for public pages (login, register, pricing). */
export function MeshBackground() {
  return (
    <div aria-hidden="true" className="fixed inset-0 -z-10 overflow-hidden bg-background">
      <div className="absolute -top-24 -left-24 size-96 rounded-full bg-violet-200/60 blur-3xl" />
      <div className="absolute top-1/3 -right-24 size-96 rounded-full bg-emerald-200/50 blur-3xl" />
      <div className="absolute -bottom-24 left-1/4 size-96 rounded-full bg-orange-200/50 blur-3xl" />
      <div className="absolute right-1/3 bottom-1/4 size-64 rounded-full bg-sky-200/50 blur-3xl" />
    </div>
  )
}
