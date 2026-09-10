const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const evidence = path.join(root, "docs", "evidence");
fs.mkdirSync(evidence, { recursive: true });
const browserExecutable = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
].find(candidate => fs.existsSync(candidate));

const plans = [
  { id: 1, name: "Express", description: "Navegación rápida y mensajería.", price: "25.00", duration_minutes: 30, is_active: true, created_at: "2026-01-01T00:00:00Z" },
  { id: 2, name: "Focus", description: "Trabajo concentrado y videollamadas.", price: "45.00", duration_minutes: 120, is_active: true, created_at: "2026-01-01T00:00:00Z" },
  { id: 3, name: "Productivity", description: "Una jornada productiva completa.", price: "80.00", duration_minutes: 480, is_active: true, created_at: "2026-01-01T00:00:00Z" },
  { id: 4, name: "Unlimited Day", description: "Acceso durante todo el día.", price: "120.00", duration_minutes: 1440, is_active: true, created_at: "2026-01-01T00:00:00Z" }
];

function staticFile(urlPath) {
  const admin = urlPath.startsWith("/admin/");
  const relative = admin ? urlPath.slice(7) : urlPath === "/" ? "index.html" : urlPath.slice(1);
  const base = path.join(root, admin ? "admin" : "frontend");
  const candidate = path.resolve(base, relative.split("?")[0]);
  if (!candidate.startsWith(base)) return null;
  return candidate;
}

const server = http.createServer((req, res) => {
  if (req.url === "/favicon.ico") { res.writeHead(204); res.end(); return; }
  const file = staticFile(req.url);
  if (!file || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404); res.end("Not found"); return;
  }
  const ext = path.extname(file);
  const types = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".png": "image/png", ".jpeg": "image/jpeg" };
  res.writeHead(200, { "Content-Type": types[ext] || "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
});

async function mockApi(page, role = "super_admin") {
  await page.addInitScript(() => localStorage.setItem("cofinet_admin_token", "visual-qa-token"));
  await page.route("**/api/**", async route => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/admin/me") {
      return route.fulfill({ json: { id: 1, email: "qa@example.test", full_name: role === "super_admin" ? "QA Super Admin" : "QA Operador", role, is_active: true, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", last_login_at: null, created_by_admin_id: null } });
    }
    if (url.pathname === "/api/plans") return route.fulfill({ json: plans });
    if (url.pathname.startsWith("/api/admin/plans/")) return route.fulfill({ json: plans[0] });
    return route.fulfill({ status: 404, json: { detail: "QA mock" } });
  });
}

async function portalShot(browser, viewport, name) {
  const page = await browser.newPage({ viewport });
  const errors = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));
  page.on("response", response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
  await page.route(/^https:\/\//, route => route.fulfill({ status: 204, body: "" }));
  await page.route("**/api/plans", route => route.fulfill({ json: plans }));
  await page.goto("http://127.0.0.1:41731/", { waitUntil: "domcontentloaded" });
  await page.addStyleTag({ content: ".portal-shell{margin-left:auto!important;margin-right:auto!important;width:100%}.grid{display:grid}.flex{display:flex}.flex-col{flex-direction:column}.w-full{width:100%}.hidden{display:none!important}@media(min-width:768px){.md\\:block{display:block!important}.md\\:hidden{display:none!important}}" });
  await page.waitForSelector(".portal-welcome__logo");
  await page.waitForFunction(() => document.querySelector(".portal-welcome__logo").complete);
  const checks = await page.evaluate(() => {
    const logo = document.querySelector(".portal-welcome__logo");
    const rect = logo.getBoundingClientRect();
    const accessDescription = document.querySelector('#desktop-inicio [data-access-card="code"] p') || document.querySelector(".mobile-access-card--code p");
    return {
      natural: [logo.naturalWidth, logo.naturalHeight],
      rendered: [Math.round(rect.width), Math.round(rect.height)],
      ratioDifference: Math.abs((rect.width / rect.height) - (logo.naturalWidth / logo.naturalHeight)),
      heading: document.querySelector("#portal-welcome-title").textContent.trim(),
      overflow: document.documentElement.scrollWidth - window.innerWidth,
      descriptionColor: accessDescription ? getComputedStyle(accessDescription).color : null
    };
  });
  await page.screenshot({ path: path.join(evidence, name), fullPage: false });
  await page.close();
  if (checks.natural[0] < checks.rendered[0] || checks.ratioDifference > 0.02 || checks.overflow > 0 || !checks.heading.includes("HOLA") || errors.length) {
    throw new Error(`${name} failed: ${JSON.stringify({ checks, errors })}`);
  }
  return { name, checks, errors };
}

async function adminShot(browser, role, name, openEditor) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(error.message));
  await mockApi(page, role);
  await page.goto("http://127.0.0.1:41731/admin/plans.html", { waitUntil: "networkidle" });
  await page.waitForSelector(".plan-card");
  const editCount = await page.locator(".plan-card-heading button").count();
  if (openEditor) await page.locator(".plan-card-heading button").first().click();
  await page.screenshot({ path: path.join(evidence, name), fullPage: true });
  await page.close();
  if ((role === "super_admin" && editCount !== 4) || (role !== "super_admin" && editCount !== 0) || errors.length) {
    throw new Error(`${name} failed: ${JSON.stringify({ editCount, errors })}`);
  }
  return { name, editCount, errors };
}

server.listen(41731, "127.0.0.1", async () => {
  let browser;
  try {
    browser = await chromium.launch({
      headless: true,
      ...(browserExecutable ? { executablePath: browserExecutable } : {})
    });
    const results = [];
    results.push(await portalShot(browser, { width: 1440, height: 1000 }, "portal-desktop.png"));
    results.push(await portalShot(browser, { width: 390, height: 844 }, "portal-mobile.png"));
    results.push(await adminShot(browser, "super_admin", "admin-plans-super.png", true));
    results.push(await adminShot(browser, "pin_operator", "admin-plans-operator.png", false));
    process.stdout.write(JSON.stringify(results, null, 2));
  } catch (error) {
    console.error(error);
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    server.close();
  }
});
