import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot, hydrateRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "sonner";
import App from "@/App";
import { AuthProvider } from "@/context/AuthContext";
import { STATIC_CONFIG } from "@/lib/seo";
// Fonts are bundled with the app (no Google CDN call): Tamil + Latin from Indian type foundries.
import "@fontsource-variable/anek-tamil/wdth.css";
import "@fontsource/anek-tamil/500.css";
import "@fontsource/anek-tamil/600.css";
import "@fontsource/anek-tamil/700.css";
import "@fontsource/hind-madurai/400.css";
import "@fontsource/hind-madurai/500.css";
import "@fontsource/hind-madurai/600.css";
import "@/index.css";

const queryClient = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false } } });

const root = document.getElementById("root");
if (!root) throw new Error("Missing #root element in index.html");

const tree = (
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <App />
          <Toaster position="top-center" richColors toastOptions={{ style: { fontFamily: "Hind Madurai, sans-serif", fontSize: "15px" } }} />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>
);

// Public pages arrive as prebuilt HTML (scripts/prerender.mjs): reuse it instead of drawing the page again.
if (root.hasChildNodes()) {
  queryClient.setQueryData(["public-config"], STATIC_CONFIG);
  hydrateRoot(root, tree);
  setTimeout(() => queryClient.invalidateQueries({ queryKey: ["public-config"] }), 0);
} else {
  createRoot(root).render(tree);
}

// Lets owners add Virundhu to their phone's home screen (production builds only).
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => undefined);
  });
}
