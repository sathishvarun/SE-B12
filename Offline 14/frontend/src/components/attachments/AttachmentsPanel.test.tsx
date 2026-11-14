import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { toast } from "sonner"

import { MAX_FILE_SIZE_BYTES, uploadAttachment, validateFile } from "@/services/attachments"
import type { Attachment } from "@/types"

import AttachmentsPanel from "./AttachmentsPanel"

vi.mock("sonner", () => ({
  toast: { success: vi.fn<(message: string) => void>(), error: vi.fn<(message: string) => void>() },
}))

vi.mock("@/services/attachments", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/services/attachments")>()
  return { ...actual, uploadAttachment: vi.fn<typeof actual.uploadAttachment>() }
})

const uploadMock = vi.mocked(uploadAttachment)

/** A File whose reported size is `size` bytes without allocating that much memory. */
function fileOfSize(name: string, size: number, type = "application/pdf"): File {
  const file = new File(["x"], name, { type })
  Object.defineProperty(file, "size", { value: size })
  return file
}

afterEach(() => {
  vi.clearAllMocks()
})

describe("validateFile", () => {
  it.each(["report.pdf", "photo.png", "photo.jpg", "photo.JPEG", "notes.docx", "sheet.xlsx"])(
    "accepts %s",
    (name) => {
      expect(validateFile(fileOfSize(name, 100))).toBeNull()
    },
  )

  it.each(["virus.exe", "notes.txt", "archive.zip", "noextension", "report.pdf.exe"])("rejects %s", (name) => {
    expect(validateFile(fileOfSize(name, 100))).toMatch(/is not a supported file type/)
  })

  it("accepts exactly 10 MB and rejects anything larger", () => {
    expect(MAX_FILE_SIZE_BYTES).toBe(10 * 1024 * 1024)
    expect(validateFile(fileOfSize("big.pdf", MAX_FILE_SIZE_BYTES))).toBeNull()
    expect(validateFile(fileOfSize("big.pdf", MAX_FILE_SIZE_BYTES + 1))).toBe(
      '"big.pdf" is too large. The maximum size is 10 MB.',
    )
  })
})

describe("AttachmentsPanel uploads", () => {
  const uploaded: Attachment = {
    id: 1,
    filename: "report.pdf",
    content_type: "application/pdf",
    size_bytes: 100,
    contact_id: 3,
    deal_id: null,
    created_at: "2026-01-01T00:00:00Z",
  }

  function pick(files: File[]) {
    const onChange = vi.fn<() => void>()
    render(<AttachmentsPanel contactId={3} attachments={[]} onChange={onChange} />)
    fireEvent.change(screen.getByLabelText("Upload attachment"), { target: { files } })
    return onChange
  }

  it("rejects bad type and oversize files without calling the API", async () => {
    const onChange = pick([fileOfSize("virus.exe", 10), fileOfSize("huge.pdf", MAX_FILE_SIZE_BYTES + 1)])

    await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(2))
    expect(vi.mocked(toast.error).mock.calls[0][0]).toMatch(/not a supported file type/)
    expect(vi.mocked(toast.error).mock.calls[1][0]).toMatch(/too large/)
    expect(uploadMock).not.toHaveBeenCalled()
    expect(onChange).not.toHaveBeenCalled()
  })

  it("uploads valid files to the right parent and notifies the parent", async () => {
    uploadMock.mockResolvedValue(uploaded)
    const good = fileOfSize("report.pdf", 100)
    const onChange = pick([good, fileOfSize("bad.txt", 10)])

    await waitFor(() => expect(onChange).toHaveBeenCalledTimes(1))
    expect(uploadMock).toHaveBeenCalledTimes(1)
    expect(uploadMock.mock.calls[0][0]).toBe(good)
    expect(uploadMock.mock.calls[0][1]).toEqual({ contactId: 3, dealId: undefined })
    expect(toast.success).toHaveBeenCalledWith('Uploaded "report.pdf"')
  })
})
