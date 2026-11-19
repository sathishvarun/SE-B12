/** Server-side entry used only at build time by scripts/prerender.mjs to write real HTML for the public pages. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { prerenderToNodeStream } from "react-dom/static";
import { StaticRouter } from "react-router-dom";
import { Toaster } from "sonner";
import App from "@/App";
import { AuthProvider } from "@/context/AuthContext";
import { STATIC_CONFIG } from "@/lib/seo";

export async function render(url: string): Promise<string> {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, enabled: false } } });
  queryClient.setQueryData(["public-config"], STATIC_CONFIG);
  const { prelude } = await prerenderToNodeStream(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <StaticRouter location={url}>
          <App />
          <Toaster position="top-center" richColors toastOptions={{ style: { fontFamily: "Hind Madurai, sans-serif", fontSize: "15px" } }} />
        </StaticRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
  const decoder = new TextDecoder();
  let html = "";
  for await (const c of prelude as AsyncIterable<Uint8Array>) html += decoder.decode(c, { stream: true });
  return html + decoder.decode();
}

export * as seo from "@/lib/seo";
