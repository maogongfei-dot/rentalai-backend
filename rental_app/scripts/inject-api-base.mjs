// inject-api-base.mjs — Vercel or CI: inject API base URL into static HTML under web_public.
// Static site root is rental_app/web_public (no dist output folder).
//
// Environment (resolved base URL, first non-empty wins):
//   1. VITE_RENTALAI_API_BASE
//   2. RENTALAI_API_BASE
//   3. NEXT_PUBLIC_RENTALAI_API_BASE
//   4. VITE_API_BASE_URL
//
// The meta tag "vite-rentalai-api-base" is filled only from VITE_RENTALAI_API_BASE (for runtime priority in api_config.js).
// If no env vars are set, exits 0 without modifying files (same-origin local dev).

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const staticRoot = path.join(__dirname, "..", "web_public");

function pickEnv(...keys) {
  for (const k of keys) {
    const v = (process.env[k] || "").trim();
    if (v) return v;
  }
  return "";
}

function stripSlash(s) {
  return s.replace(/\/$/, "");
}

function escapeAttr(s) {
  return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
}

function patchMetaContent(html, metaName, newContent) {
  const esc = escapeAttr(newContent);
  const safeName = metaName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(
    "(<meta\\s+name=\"" + safeName + "\"\\s+content=\")([^\"]*)(\")",
    "gi",
  );
  const next = html.replace(re, `$1${esc}$3`);
  return { html: next, changed: next !== html };
}

const viteOnly = stripSlash(pickEnv("VITE_RENTALAI_API_BASE"));
const resolved = stripSlash(
  pickEnv(
    "VITE_RENTALAI_API_BASE",
    "RENTALAI_API_BASE",
    "NEXT_PUBLIC_RENTALAI_API_BASE",
    "VITE_API_BASE_URL",
  ),
);

if (!resolved && !viteOnly) {
  console.log(
    "inject-api-base: no API base env set; leaving meta tags empty (same-origin).",
  );
  process.exit(0);
}

const viteToWrite = viteOnly;
const rentalToWrite = resolved || viteOnly;

function walk(dir) {
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    const st = fs.statSync(p);
    if (st.isDirectory()) walk(p);
    else if (name.endsWith(".html")) {
      let html = fs.readFileSync(p, "utf8");
      let changed = false;
      let r = patchMetaContent(html, "vite-rentalai-api-base", viteToWrite);
      if (r.changed) {
        html = r.html;
        changed = true;
      }
      r = patchMetaContent(html, "rentalai-api-base", rentalToWrite);
      if (r.changed) {
        html = r.html;
        changed = true;
      }
      if (changed) {
        fs.writeFileSync(p, html, "utf8");
        console.log("inject-api-base: patched", path.relative(staticRoot, p));
      }
    }
  }
}

walk(staticRoot);
console.log(
  "inject-api-base: vite meta =",
  viteToWrite || "(empty)",
  "| rentalai-api-base =",
  rentalToWrite,
);
