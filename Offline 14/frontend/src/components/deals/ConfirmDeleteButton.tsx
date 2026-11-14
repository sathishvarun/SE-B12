import { useTranslation } from "react-i18next"
import { useState } from "react"
import { Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

interface ConfirmDeleteButtonProps {
  /** What is being deleted, e.g. "deal" or "task". */
  itemName: string
  isDeleting?: boolean
  onConfirm: () => void
}

/** "Delete" button that asks for confirmation in a dialog first. */
export function ConfirmDeleteButton({ itemName, isDeleting = false, onConfirm }: ConfirmDeleteButtonProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="destructive">
          <Trash2 /> {t("common.delete")}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("deals.confirmDeleteTitle", { item: itemName })}</DialogTitle>
          <DialogDescription>{t("deals.confirmDeleteText")}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">{t("common.cancel")}</Button>
          </DialogClose>
          <Button
            variant="destructive"
            disabled={isDeleting}
            onClick={() => {
              onConfirm()
              setOpen(false)
            }}
          >
            {isDeleting ? t("common.deleting") : t("deals.confirmDeleteButton", { item: itemName })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
