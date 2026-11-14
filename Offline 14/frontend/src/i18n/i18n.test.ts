import { STAGE_LABELS } from "@/components/deals/format"
import { MAIN_SECTIONS } from "@/lib/sections"

import i18n, { formatLocale } from "."

describe("i18n", () => {
  afterEach(async () => {
    await i18n.changeLanguage("en")
  })

  it("switches labels to Tamil and back", async () => {
    expect(STAGE_LABELS.won).toBe("Won")
    expect(MAIN_SECTIONS[0].label).toBe("Dashboard")

    await i18n.changeLanguage("ta")
    expect(STAGE_LABELS.won).toBe("வென்றது")
    expect(MAIN_SECTIONS[0].label).toBe("டாஷ்போர்டு")
    expect(formatLocale()).toBe("ta-IN")
    expect(document.documentElement.lang).toBe("ta")
  })

  it("uses the right plural form", async () => {
    expect(i18n.t("deals.dealsInColumn", { count: 1 })).toBe("1 deal")
    expect(i18n.t("deals.dealsInColumn", { count: 3 })).toBe("3 deals")
    await i18n.changeLanguage("ta")
    expect(i18n.t("dashboard.taskCount", { count: 2 })).toBe("2 பணிகள்")
  })
})
