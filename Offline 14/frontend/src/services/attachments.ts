import i18n from "@/i18n"
import api from "@/services/api"
import type { Attachment } from "@/types"

export const ALLOWED_EXTENSIONS = ["pdf", "png", "jpg", "jpeg", "docx", "xlsx"]
export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

export interface AttachmentTarget {
  contactId?: number
  dealId?: number
}

/** Returns a friendly error message if the file can't be uploaded, otherwise null. */
export function validateFile(file: File): string | null {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? ""
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return i18n.t("errors.fileType", { name: file.name, allowed: ALLOWED_EXTENSIONS.join(", ") })
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return i18n.t("errors.fileTooLarge", { name: file.name })
  }
  return null
}

export async function uploadAttachment(
  file: File,
  target: AttachmentTarget,
  onProgress?: (percent: number) => void,
): Promise<Attachment> {
  const form = new FormData()
  form.append("file", file)
  if (target.contactId !== undefined) form.append("contact_id", String(target.contactId))
  if (target.dealId !== undefined) form.append("deal_id", String(target.dealId))

  const { data } = await api.post<Attachment>("/attachments", form, {
    // The shared client defaults to JSON; this makes axios send the FormData as-is
    // (the browser then sets the multipart boundary itself).
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    },
  })
  return data
}

/** Fetch the file with the auth header, then trigger a normal browser download. */
export async function downloadAttachment(attachment: Attachment): Promise<void> {
  const { data } = await api.get<Blob>(`/attachments/${attachment.id}`, { responseType: "blob" })
  const url = URL.createObjectURL(data)
  const link = document.createElement("a")
  link.href = url
  link.download = attachment.filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export async function deleteAttachment(id: number): Promise<void> {
  await api.delete(`/attachments/${id}`)
}
