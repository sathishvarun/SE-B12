/** Red validation message under a form field (renders nothing when there is no error). */
export function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return <p className="text-sm text-destructive">{message}</p>
}
