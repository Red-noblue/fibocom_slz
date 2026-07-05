const { chromium } = require("../node_modules/playwright");

async function check(mode) {
  const browser = await chromium.launch({
    headless: true,
    args: ["--use-gl=swiftshader", "--disable-gpu-sandbox"],
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on("console", (msg) => {
    if (["error", "warning"].includes(msg.type())) {
      const text = msg.text();
      if (!text.includes("GPU stall due to ReadPixels")) {
        errors.push(`${msg.type()}: ${text}`);
      }
    }
  });
  page.on("pageerror", (err) => errors.push(`pageerror: ${err.message}`));
  page.on("requestfailed", (req) => {
    const failure = req.failure();
    errors.push(`requestfailed: ${req.url()} ${failure ? failure.errorText : ""}`);
  });

  await page.goto("http://127.0.0.1:8090/?v=check", {
    waitUntil: "networkidle",
    timeout: 120000,
  });
  if (mode === "safe") {
    await page.selectOption("#building-backend", "none");
    await page.uncheck("#layer-buildings");
  }
  if (mode === "tiles" || mode === "default") {
    await page.selectOption("#building-backend", "tiles");
    if (!(await page.isChecked("#layer-buildings"))) {
      await page.check("#layer-buildings");
    }
  }
  await page.waitForTimeout(8000);
  const status = await page.textContent("#load-status").catch(() => "NO_STATUS");
  const bodyText = await page.textContent("body").catch(() => "");
  await page.screenshot({ path: `/tmp/uav_web_${mode}.png`, fullPage: false });
  await browser.close();
  return {
    mode,
    status,
    hasRenderingStopped: bodyText.includes("Rendering has stopped"),
    errors,
  };
}

(async () => {
  const results = [await check("default"), await check("safe"), await check("tiles")];
  console.log(JSON.stringify(results, null, 2));
  const failed = results.some((item) => item.status !== "世界已加载" || item.hasRenderingStopped || item.errors.length);
  process.exit(failed ? 1 : 0);
})();
