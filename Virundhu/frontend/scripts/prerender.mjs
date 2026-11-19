// Writes real HTML for every public page after `vite build`, so Google and link previews see the text and each page's
// own title, description, canonical and structured data. The signed-in app stays a normal single-page app.
//   dist/index.html            the home page, prerendered
//   dist/<path>/index.html     every other public page
//   dist/app-shell.html        empty shell (noindex) that nginx serves for /app, /login, /f/... routes
//   dist/404.html              "not on the menu" page, served with a real 404 status
//   dist/sitemap.xml
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(root, "dist");
const { render, seo } = await import(pathToFileURL(join(root, "dist-ssr", "entry-server.js")).href);
const { SEO, PUBLIC_PATHS, NOT_FOUND_SEO, SITE_URL, headHtml } = seo;

const template = readFileSync(join(dist, "index.html"), "utf8");
// Strip the template's default head tags; each page gets its own.
const base = template
  .replace(/<title>[\s\S]*?<\/title>\s*/, "")
  .replace(/<meta name="description"[^>]*>\s*/, "")
  .replace(/<meta property="og:[^>]*>\s*/g, "");

const page = (head, body) =>
  base.replace("</head>", `    ${head}\n  </head>`).replace('<div id="root"></div>', `<div id="root">${body}</div>`);

writeFileSync(join(dist, "app-shell.html"), page(headHtml("/app", { title: "Virundhu", description: SEO["/"].description }, true), ""));

let count = 0;
for (const path of PUBLIC_PATHS) {
  const body = await render(path);
  const out = path === "/" ? join(dist, "index.html") : join(dist, path.slice(1), "index.html");
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, page(headHtml(path, SEO[path]), body));
  count += 1;
}
writeFileSync(join(dist, "404.html"), page(headHtml("/404", NOT_FOUND_SEO, true), await render("/this-page-is-not-on-the-menu")));

const today = new Date().toISOString().slice(0, 10);
const urls = PUBLIC_PATHS.map((p) => {
  const priority = p === "/" ? "1.0" : ["/how-it-works", "/pricing", "/contact", "/compare", "/about"].includes(p) ? "0.8" : "0.4";
  return `  <url><loc>${SITE_URL}${p}</loc><lastmod>${today}</lastmod><priority>${priority}</priority></url>`;
});
writeFileSync(
  join(dist, "sitemap.xml"),
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join("\n")}\n</urlset>\n`,
);
console.log(`Prerendered ${count} public pages, 404 page, app shell and sitemap.`);
