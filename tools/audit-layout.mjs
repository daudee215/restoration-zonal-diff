#!/usr/bin/env node
/**
 * audit-layout.mjs — Layout / UI-UX gate for gisgap tools.
 *
 * Runs the standing seven-rule layout audit (see memory:
 * feedback_ui_ux_standard.md) against a live or local URL at four
 * breakpoints. Emits a JSON report and per-breakpoint screenshots.
 * Exits 1 if any rule is violated, 0 otherwise.
 *
 * Usage:
 *   node tools/audit-layout.mjs                          # audits ./index.html
 *   AUDIT_URL=https://daudee215.github.io/gisgap-uav-structure/ \
 *     node tools/audit-layout.mjs                        # audits a live URL
 *   node tools/audit-layout.mjs --json-only              # no screenshots
 *
 * Output:
 *   audit-report.json
 *   screenshots/{w}px.png
 *
 * Exit codes:
 *   0  all rules pass
 *   1  one or more violations
 *   2  setup error (browser launch, page load timeout)
 */

import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import process from "node:process";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");

// Breakpoints required by feedback_ui_ux_standard.md rule 4.
const BREAKPOINTS = [
  { width: 360,  height: 780,  label: "mobile-narrow" },
  { width: 920,  height: 900,  label: "tablet" },
  { width: 1180, height: 900,  label: "desktop-min" },
  { width: 1440, height: 900,  label: "desktop-wide" },
];

const PAGE_LOAD_TIMEOUT = 20_000;
const REPORT_FILE = path.join(REPO_ROOT, "audit-report.json");
const SCREENSHOT_DIR = path.join(REPO_ROOT, "screenshots");

const args = new Set(process.argv.slice(2));
const SCREENSHOTS_ENABLED = !args.has("--json-only");

// ─────────────────────────────────────────────────────────────────────
// Local static server (only used when AUDIT_URL is not set)
// ─────────────────────────────────────────────────────────────────────
async function startLocalServer() {
  const port = 4173;
  const url = `http://localhost:${port}/`;
  const server = spawn("python3", ["-m", "http.server", String(port)], {
    cwd: REPO_ROOT,
    stdio: ["ignore", "ignore", "pipe"],
  });
  // Poll until the server actually answers (up to ~5s). `python3 -m
  // http.server` can take noticeably longer than 600ms to bind under
  // CI runners with cold caches.
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(500) });
      if (res.ok || res.status === 404) break;
    } catch {
      await new Promise(r => setTimeout(r, 150));
    }
  }
  return {
    url,
    stop: () => { try { server.kill("SIGTERM"); } catch {} },
  };
}

// ─────────────────────────────────────────────────────────────────────
// Audit rules. Each returns { rule, passed, evidence }.
// Rules are intentionally generic — they look for symptoms, not for
// a specific tool's class names. Drop-in for any gisgap tool.
// ─────────────────────────────────────────────────────────────────────
async function auditPage(page, viewport) {
  const results = [];

  // Rule 1: no horizontal scroll. Page must fit within its viewport.
  results.push(await page.evaluate((vw) => {
    const docW = document.documentElement.scrollWidth;
    const winW = window.innerWidth;
    return {
      rule: "no-horizontal-scroll",
      passed: docW <= winW + 1,
      evidence: { documentScrollWidth: docW, viewportWidth: winW, viewport: vw },
    };
  }, viewport.width));

  // Rule 2: topbar items vertically centered, not bottom-aligned.
  results.push(await page.evaluate(() => {
    const bar = document.querySelector(".topbar, header, [role='banner']");
    if (!bar) {
      return { rule: "topbar-vertical-alignment", passed: true, evidence: { skipped: "no topbar found" } };
    }
    const cs = getComputedStyle(bar);
    const isFlexOrGrid = cs.display === "grid" || cs.display === "flex";
    // For flex-direction: column, align-items controls cross-axis
    // (horizontal) alignment, so the rule doesn't apply.
    const isColumn = cs.flexDirection && cs.flexDirection.startsWith("column");
    const ok = !isFlexOrGrid || isColumn || ["center", "baseline"].includes(cs.alignItems);
    return {
      rule: "topbar-vertical-alignment",
      passed: ok,
      evidence: { display: cs.display, alignItems: cs.alignItems, flexDirection: cs.flexDirection },
    };
  }));

  // Rule 3: visible inputs/buttons/selects must not sit on the absolute
  // left edge of their parent container by accident.
  results.push(await page.evaluate(() => {
    const interactive = [...document.querySelectorAll(
      "input:not([type='checkbox']):not([type='radio']):not([type='hidden']), " +
      "select, button:not([aria-label*='close']), .btn, [role='button']"
    )].filter(el => el.offsetParent !== null);

    const offenders = [];
    for (const el of interactive) {
      const parent = el.parentElement;
      if (!parent) continue;
      const elBox = el.getBoundingClientRect();
      const parentBox = parent.getBoundingClientRect();
      const leftOffset = elBox.left - parentBox.left;
      const rightOffset = parentBox.right - elBox.right;
      if (parentBox.width - elBox.width < 4) continue;
      // Skip if any visible sibling extends to the right of this element —
      // the rightOffset gap is occupied, not empty.
      const sibs = [...el.parentElement.children]
        .filter(s => s !== el && s.offsetParent !== null);
      const hasRightSibling = sibs.some(s => s.getBoundingClientRect().right > elBox.right + 1);
      if (hasRightSibling) continue;
      if (leftOffset < 2 && rightOffset > 24) {
        offenders.push({
          tag: el.tagName.toLowerCase(),
          id: el.id || null,
          cls: el.className || null,
          leftOffset, rightOffset,
        });
      }
    }
    return {
      rule: "no-orphan-left-edge-controls",
      passed: offenders.length === 0,
      evidence: { offenders: offenders.slice(0, 5), totalOffenders: offenders.length },
    };
  }));

  // Rule 4: focusable elements must have a visible focus style.
  // Pick the first VISIBLE focusable — skip hidden inputs (e.g.
  // mkdocs-material's #__drawer toggle), disabled controls, and any
  // element with no offsetParent (display:none somewhere in the chain).
  results.push(await page.evaluate(() => {
    const candidates = [...document.querySelectorAll(
      "a[href], button, input, select, textarea, [tabindex]:not([tabindex='-1'])"
    )];
    const first = candidates.find(el =>
      el.offsetParent !== null && !el.disabled && !el.hidden
    );
    if (!first) {
      return { rule: "focus-style-defined", passed: true, evidence: { skipped: "no focusables" } };
    }
    first.focus({ preventScroll: true });
    const cs = getComputedStyle(first);
    const hasOutline = cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0;
    const hasBoxShadow = cs.boxShadow && cs.boxShadow !== "none";
    return {
      rule: "focus-style-defined",
      passed: hasOutline || hasBoxShadow,
      evidence: { outlineStyle: cs.outlineStyle, outlineWidth: cs.outlineWidth, boxShadow: cs.boxShadow },
    };
  }));

  // Rule 5: viewport meta present.
  results.push(await page.evaluate(() => {
    const meta = document.querySelector("meta[name='viewport']");
    return {
      rule: "viewport-meta-present",
      passed: !!meta,
      evidence: { content: meta?.getAttribute("content") || null },
    };
  }));

  // Rule 6: language declared on <html>.
  results.push(await page.evaluate(() => {
    const lang = document.documentElement.lang;
    return {
      rule: "html-lang-declared",
      passed: !!lang && lang.length >= 2,
      evidence: { lang },
    };
  }));

  // Rule 7: page title non-empty and descriptive (>10 chars).
  results.push(await page.evaluate(() => {
    const title = document.title || "";
    return {
      rule: "page-title-descriptive",
      passed: title.trim().length >= 10,
      evidence: { title },
    };
  }));

  // Rule 8: at narrow breakpoints, multi-column grids must not have
  // a sum of fixed-pixel tracks that exceeds the viewport. Computed
  // gridTemplateColumns always resolves to pixels, so we read it as
  // the actual rendered widths and check whether the grid itself is
  // wider than its container — that's the real symptom.
  results.push(await page.evaluate((vw) => {
    if (vw > 1180) {
      return { rule: "grid-shrinkable", passed: true, evidence: { skipped: "wide viewport" } };
    }
    const grids = [...document.querySelectorAll("main *, body > *")].filter(el => {
      const cs = getComputedStyle(el);
      return cs.display === "grid";
    });
    const offenders = [];
    for (const el of grids) {
      const elBox = el.getBoundingClientRect();
      const parent = el.parentElement || document.documentElement;
      const parentBox = parent.getBoundingClientRect();
      const cs = getComputedStyle(el);
      const tpl = cs.gridTemplateColumns || "";
      const colCount = tpl.trim().split(/\s+/).length;
      if (colCount < 2) continue;
      // Real symptom: grid is wider than its parent container by a
      // meaningful margin (4px slack for sub-pixel layout).
      if (elBox.width > parentBox.width + 4) {
        offenders.push({
          tag: el.tagName.toLowerCase(),
          cls: el.className || null,
          gridTemplateColumns: tpl,
          gridWidth: Math.round(elBox.width),
          parentWidth: Math.round(parentBox.width),
        });
      }
    }
    return {
      rule: "grid-shrinkable",
      passed: offenders.length === 0,
      evidence: { offenders: offenders.slice(0, 3) },
    };
  }, viewport.width));

  return results;
}

// ─────────────────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────────────────
async function main() {
  const startedAt = new Date().toISOString();

  let serverHandle = null;
  let url = process.env.AUDIT_URL;
  if (!url) {
    if (!existsSync(path.join(REPO_ROOT, "index.html"))) {
      console.error("audit-layout: no AUDIT_URL set and no index.html in repo root.");
      process.exit(2);
    }
    serverHandle = await startLocalServer();
    url = serverHandle.url;
  }

  if (SCREENSHOTS_ENABLED) {
    await mkdir(SCREENSHOT_DIR, { recursive: true });
  }

  let browser;
  try {
    browser = await chromium.launch();
  } catch (err) {
    console.error("audit-layout: failed to launch chromium:", err.message);
    console.error("Did you run `npx playwright install chromium`?");
    serverHandle?.stop();
    process.exit(2);
  }

  const breakpointReports = [];
  let allPassed = true;

  for (const bp of BREAKPOINTS) {
    const context = await browser.newContext({
      viewport: { width: bp.width, height: bp.height },
      deviceScaleFactor: 1,
      reducedMotion: "reduce",
    });
    const page = await context.newPage();

    let loadOk = true;
    try {
      await page.goto(url, { waitUntil: "load", timeout: PAGE_LOAD_TIMEOUT });
      await page.waitForTimeout(800);
    } catch (err) {
      loadOk = false;
      console.error(`audit-layout: page load failed at ${bp.width}px: ${err.message}`);
    }

    if (SCREENSHOTS_ENABLED && loadOk) {
      const file = path.join(SCREENSHOT_DIR, `${bp.width}px.png`);
      try {
        await page.screenshot({ path: file, fullPage: false });
      } catch (err) {
        console.warn(`audit-layout: screenshot failed at ${bp.width}px: ${err.message}`);
      }
    }

    let rules = [];
    if (loadOk) {
      rules = await auditPage(page, bp);
    } else {
      rules.push({
        rule: "page-loads",
        passed: false,
        evidence: { reason: "navigation timeout or error" },
      });
    }


    const passed = rules.every(r => r.passed);
    allPassed = allPassed && passed;

    breakpointReports.push({
      width: bp.width,
      height: bp.height,
      label: bp.label,
      passed,
      rules,
    });

    await context.close();

    const status = passed ? "PASS" : "FAIL";
    console.log(`[${status}] ${bp.width}px (${bp.label}) — ${rules.length} rules, ${rules.filter(r => !r.passed).length} violations`);
    for (const r of rules) {
      if (!r.passed) {
        console.log(`        x ${r.rule} :: ${JSON.stringify(r.evidence)}`);
      }
    }
  }

  await browser.close();
  serverHandle?.stop();

  const report = {
    tool: path.basename(REPO_ROOT),
    url,
    startedAt,
    finishedAt: new Date().toISOString(),
    passed: allPassed,
    breakpoints: breakpointReports,
  };

  await writeFile(REPORT_FILE, JSON.stringify(report, null, 2));
  console.log(`\nReport: ${path.relative(process.cwd(), REPORT_FILE)}`);
  if (SCREENSHOTS_ENABLED) {
    console.log(`Screenshots: ${path.relative(process.cwd(), SCREENSHOT_DIR)}/`);
  }

  process.exit(allPassed ? 0 : 1);
}

main().catch(err => {
  console.error("audit-layout: unexpected error:", err);
  process.exit(2);
});
