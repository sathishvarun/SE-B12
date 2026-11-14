import { useTranslation } from "react-i18next"
import { useRef, useState, type DragEvent } from "react"
import { Download, File, FileImage, FileSpreadsheet, FileText, Trash2, Upload } from "lucide-react"
import { toast } from "sonner"

import { AnimatedList } from "@/components/common"
import { ConfirmDialog } from "@/components/contacts/ConfirmDialog"
import { formatDate, formatFileSize } from "@/components/contacts/utils"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { getErrorMessage } from "@/services/api"
import {
  ALLOWED_EXTENSIONS,
  deleteAttachment,
  downloadAttachment,
  uploadAttachment,
  validateFile,
} from "@/services/attachments"
import type { Attachment } from "@/types"

// Keep these props stable: the Deals page uses this panel too.
export interface AttachmentsPanelProps {
  /** Exactly one of contactId / dealId is set. */
  contactId?: number
  dealId?: number
  attachments: Attachment[]
  /** Called after a successful upload or delete so the parent can refetch. */
  onChange: () => void
}

function FileIcon({ attachment }: { attachment: Attachment }) {
  const name = attachment.filename.toLowerCase()
  if (attachment.content_type.startsWith("image/") || /\.(png|jpe?g)$/.test(name)) {
    return <FileImage className="size-5 text-sky-600" />
  }
  if (name.endsWith(".xlsx")) return <FileSpreadsheet className="size-5 text-emerald-600" />
  if (name.endsWith(".pdf")) return <FileText className="size-5 text-rose-600" />
  if (name.endsWith(".docx")) return <FileText className="size-5 text-blue-600" />
  return <File className="size-5 text-muted-foreground" />
}

export default function AttachmentsPanel({ contactId, dealId, attachments, onChange }: AttachmentsPanelProps) {
  const { t } = useTranslation()
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState<{ name: string; percent: number } | null>(null)
  const [toDelete, setToDelete] = useState<Attachment | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [downloadingId, setDownloadingId] = useState<number | null>(null)

  const uploadFiles = async (files: File[]) => {
    let uploadedAny = false
    // Upload one at a time so the progress bar stays simple.
    for (const file of files) {
      const problem = validateFile(file)
      if (problem) {
        toast.error(problem)
        continue
      }
      setUploading({ name: file.name, percent: 0 })
      try {
        await uploadAttachment(file, { contactId, dealId }, (percent) =>
          setUploading({ name: file.name, percent }),
        )
        toast.success(t("attachments.uploaded", { name: file.name }))
        uploadedAny = true
      } catch (err) {
        toast.error(getErrorMessage(err))
      }
    }
    setUploading(null)
    if (uploadedAny) onChange()
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragging(false)
    if (uploading) return
    void uploadFiles(Array.from(event.dataTransfer.files))
  }

  const handleDownload = async (attachment: Attachment) => {
    setDownloadingId(attachment.id)
    try {
      await downloadAttachment(attachment)
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setDownloadingId(null)
    }
  }

  const handleDelete = async () => {
    if (!toDelete) return
    setIsDeleting(true)
    try {
      await deleteAttachment(toDelete.id)
      toast.success(t("attachments.deleted", { name: toDelete.filename }))
      setToDelete(null)
      onChange()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={cn(
          "flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-6 text-center transition-colors",
          isDragging ? "border-violet-500 bg-violet-50" : "border-border bg-white/40",
        )}
      >
        <Upload className="size-6 text-violet-600" />
        <p className="text-sm">
          {t("attachments.drop")}{" "}
          <Button
            type="button"
            variant="link"
            className="h-auto p-0"
            disabled={!!uploading}
            onClick={() => inputRef.current?.click()}
          >
            {t("attachments.browse")}
          </Button>
        </p>
        <p className="text-xs text-muted-foreground">
          {t("attachments.limits", { types: ALLOWED_EXTENSIONS.map((e) => e.toUpperCase()).join(", ") })}
        </p>
        <input
          ref={inputRef}
          type="file"
          name="files"
          multiple
          hidden
          aria-label={t("attachments.uploadAria")}
          accept={ALLOWED_EXTENSIONS.map((e) => `.${e}`).join(",")}
          onChange={(e) => {
            const files = Array.from(e.target.files ?? [])
            e.target.value = "" // allow picking the same file again later
            void uploadFiles(files)
          }}
        />
      </div>

      {uploading && (
        <div className="flex flex-col gap-1 text-sm" aria-live="polite">
          <span className="truncate">
            {t("attachments.uploading", { name: uploading.name, percent: uploading.percent })}
          </span>
          <progress
            value={uploading.percent}
            max={100}
            className="h-2 w-full overflow-hidden rounded-full [&::-moz-progress-bar]:bg-violet-500 [&::-webkit-progress-bar]:bg-muted [&::-webkit-progress-value]:bg-violet-500"
          />
        </div>
      )}

      {/* File list */}
      {attachments.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("attachments.none")}</p>
      ) : (
        <AnimatedList className="gap-2">
          {attachments.map((attachment) => (
            <div
              key={attachment.id}
              className="flex items-center justify-between gap-3 rounded-xl border bg-white/60 p-3"
            >
              <div className="flex min-w-0 items-center gap-3">
                <FileIcon attachment={attachment} />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{attachment.filename}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatFileSize(attachment.size_bytes)} - {formatDate(attachment.created_at)}
                  </p>
                </div>
              </div>
              <div className="flex shrink-0 gap-1">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={t("attachments.download", { name: attachment.filename })}
                  disabled={downloadingId === attachment.id}
                  onClick={() => void handleDownload(attachment)}
                >
                  <Download />
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={t("attachments.deleteFile", { name: attachment.filename })}
                  className="text-destructive hover:text-destructive"
                  onClick={() => setToDelete(attachment)}
                >
                  <Trash2 />
                </Button>
              </div>
            </div>
          ))}
        </AnimatedList>
      )}

      <ConfirmDialog
        open={toDelete !== null}
        onOpenChange={(open) => {
          if (!open) setToDelete(null)
        }}
        title={t("attachments.deleteTitle")}
        description={t("attachments.deleteText", { name: toDelete?.filename ?? "" })}
        isPending={isDeleting}
        onConfirm={() => void handleDelete()}
      />
    </div>
  )
}
