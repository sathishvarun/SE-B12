import axios, {
  AxiosError,
  AxiosHeaders,
  type AxiosAdapter,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios"

import { tokenStorage } from "@/lib/tokenStorage"
import api, { getErrorMessage } from "@/services/api"

type Handler = (config: InternalAxiosRequestConfig) => { status: number; data: unknown }

/** Build an axios adapter that answers from `handler` and rejects non-2xx like the real one. */
function adapterFrom(handler: Handler, calls: InternalAxiosRequestConfig[]): AxiosAdapter {
  return async (config) => {
    calls.push(config)
    const { status, data } = handler(config)
    const response: AxiosResponse = { data, status, statusText: String(status), headers: {}, config }
    if (status >= 400) {
      throw new AxiosError(`Request failed with status code ${status}`, "ERR_BAD_REQUEST", config, null, response)
    }
    return response
  }
}

const apiCalls: InternalAxiosRequestConfig[] = []
const refreshCalls: InternalAxiosRequestConfig[] = []
const originalApiAdapter = api.defaults.adapter
const originalAxiosAdapter = axios.defaults.adapter

function authHeader(config: InternalAxiosRequestConfig): string | undefined {
  return AxiosHeaders.from(config.headers).get("Authorization")?.toString()
}

function setup(apiHandler: Handler, refreshHandler: Handler) {
  api.defaults.adapter = adapterFrom(apiHandler, apiCalls)
  // the refresh call uses plain axios, not the `api` instance
  axios.defaults.adapter = adapterFrom(refreshHandler, refreshCalls)
}

let assignSpy: ReturnType<typeof vi.fn<(url: string | URL) => void>>

beforeEach(() => {
  apiCalls.length = 0
  refreshCalls.length = 0
  tokenStorage.setTokens("old-access", "old-refresh")
  assignSpy = vi.fn<(url: string | URL) => void>()
  vi.spyOn(window, "location", "get").mockReturnValue({
    ...window.location,
    pathname: "/contacts",
    assign: assignSpy,
  })
})

afterEach(() => {
  api.defaults.adapter = originalApiAdapter
  axios.defaults.adapter = originalAxiosAdapter
  tokenStorage.clear()
  vi.restoreAllMocks()
})

describe("api client", () => {
  it("attaches the access token to requests", async () => {
    setup(() => ({ status: 200, data: { ok: true } }), () => ({ status: 500, data: null }))
    const { data } = await api.get("/contacts")
    expect(data).toEqual({ ok: true })
    expect(authHeader(apiCalls[0])).toBe("Bearer old-access")
  })

  it("refreshes the token once on 401 and retries the request", async () => {
    setup(
      (config) =>
        authHeader(config) === "Bearer new-access"
          ? { status: 200, data: { items: [] } }
          : { status: 401, data: { detail: "Invalid or expired token" } },
      () => ({ status: 200, data: { access_token: "new-access", refresh_token: "new-refresh", token_type: "bearer" } }),
    )

    const { data } = await api.get("/contacts")

    expect(data).toEqual({ items: [] })
    expect(refreshCalls).toHaveLength(1)
    expect(refreshCalls[0].url).toMatch(/\/auth\/refresh$/)
    expect(JSON.parse(String(refreshCalls[0].data))).toEqual({ refresh_token: "old-refresh" })
    expect(apiCalls).toHaveLength(2)
    expect(tokenStorage.getAccessToken()).toBe("new-access")
    expect(tokenStorage.getRefreshToken()).toBe("new-refresh")
  })

  it("shares one refresh between concurrent 401s", async () => {
    setup(
      (config) =>
        authHeader(config) === "Bearer new-access" ? { status: 200, data: "ok" } : { status: 401, data: {} },
      () => ({ status: 200, data: { access_token: "new-access", refresh_token: "new-refresh", token_type: "bearer" } }),
    )

    const results = await Promise.all([api.get("/a"), api.get("/b"), api.get("/c")])

    expect(results.map((r) => r.data)).toEqual(["ok", "ok", "ok"])
    expect(refreshCalls).toHaveLength(1)
  })

  it("clears tokens and redirects to /login when the refresh fails", async () => {
    setup(
      () => ({ status: 401, data: { detail: "expired" } }),
      () => ({ status: 401, data: { detail: "Invalid or expired refresh token" } }),
    )

    await expect(api.get("/contacts")).rejects.toMatchObject({ response: { status: 401 } })
    expect(tokenStorage.getAccessToken()).toBeNull()
    expect(tokenStorage.getRefreshToken()).toBeNull()
    expect(assignSpy).toHaveBeenCalledWith("/login")
  })

  it("does not try to refresh when there is no refresh token", async () => {
    tokenStorage.clear()
    setup(() => ({ status: 401, data: {} }), () => ({ status: 200, data: {} }))
    await expect(api.get("/contacts")).rejects.toBeInstanceOf(AxiosError)
    expect(refreshCalls).toHaveLength(0)
  })

  it("does not redirect from public pages", async () => {
    vi.spyOn(window, "location", "get").mockReturnValue({
      ...window.location,
      pathname: "/register",
      assign: assignSpy,
    })
    setup(() => ({ status: 401, data: {} }), () => ({ status: 401, data: {} }))
    await expect(api.get("/auth/me")).rejects.toBeInstanceOf(AxiosError)
    expect(assignSpy).not.toHaveBeenCalled()
  })

  it.each(["/auth/login", "/auth/register"])("never refreshes on a 401 from %s", async (path) => {
    setup(() => ({ status: 401, data: { detail: "Incorrect email or password" } }), () => ({ status: 200, data: {} }))
    await expect(api.post(path, {})).rejects.toMatchObject({ response: { status: 401 } })
    expect(refreshCalls).toHaveLength(0)
    expect(apiCalls).toHaveLength(1)
    expect(tokenStorage.getAccessToken()).toBe("old-access")
  })

  it("passes non-401 errors straight through", async () => {
    setup(() => ({ status: 404, data: { detail: "Contact not found" } }), () => ({ status: 200, data: {} }))
    await expect(api.get("/contacts/1")).rejects.toMatchObject({ response: { status: 404 } })
    expect(refreshCalls).toHaveLength(0)
  })
})

describe("getErrorMessage", () => {
  function axiosErrorWith(status: number, data: unknown): AxiosError {
    const config = { headers: new AxiosHeaders() }
    const response: AxiosResponse = { data, status, statusText: "", headers: {}, config }
    return new AxiosError("Request failed", "ERR_BAD_REQUEST", config, null, response)
  }

  it("uses a string detail", () => {
    expect(getErrorMessage(axiosErrorWith(409, { detail: "Email is already registered" }))).toBe(
      "Email is already registered",
    )
  })

  it("joins validation error messages", () => {
    const err = axiosErrorWith(422, { detail: [{ loc: ["body", "email"], msg: "bad email", type: "x" }, { loc: [], msg: "too short", type: "y" }] })
    expect(getErrorMessage(err)).toBe("bad email, too short")
  })

  it("explains network failures", () => {
    expect(getErrorMessage(new AxiosError("Network Error", "ERR_NETWORK"))).toBe(
      "Cannot reach the server. Please check your connection.",
    )
  })

  it("handles plain errors and unknown values", () => {
    expect(getErrorMessage(new Error("boom"))).toBe("boom")
    expect(getErrorMessage("nope")).toBe("Something went wrong. Please try again.")
  })
})
