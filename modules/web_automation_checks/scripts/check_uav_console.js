// 项目级浏览器自动化检查：用于无人化验证 Web 控制台加载、交互和关键渲染状态。
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const TARGET_URL = process.env.UAV_WEB_URL || "http://127.0.0.1:8090/?v=automation";
const OUTPUT_DIR = process.env.UAV_CHECK_OUTPUT_DIR || path.resolve(__dirname, "../../uav_virtual_validation/outputs/automation_checks");

function relevantErrors(errors) {
  return errors.filter((text) => !text.includes("GPU stall due to ReadPixels"));
}

async function waitForWorldReady(page) {
  await page.waitForFunction(() => {
    const text = document.querySelector("#load-status")?.textContent || "";
    return text.includes("世界已加载") || text.includes("加载失败");
  }, null, { timeout: 30000 }).catch(() => {});
}

async function check(mode) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    args: ["--use-gl=swiftshader", "--disable-gpu-sandbox"],
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on("console", (msg) => {
    if (["error", "warning"].includes(msg.type())) {
      errors.push(`${msg.type()}: ${msg.text()}`);
    }
  });
  page.on("pageerror", (err) => errors.push(`pageerror: ${err.message}`));
  page.on("requestfailed", (req) => {
    const failure = req.failure();
    errors.push(`requestfailed: ${req.url()} ${failure ? failure.errorText : ""}`);
  });

  await page.goto(TARGET_URL, { waitUntil: "networkidle", timeout: 120000 });
  if (mode === "safe") {
    await page.selectOption("#building-backend", "none");
    if (await page.isChecked("#layer-buildings")) {
      await page.uncheck("#layer-buildings");
    }
  }
  if (mode === "tiles" || mode === "drag") {
    await page.selectOption("#building-backend", "tiles");
    if (!(await page.isChecked("#layer-buildings"))) {
      await page.check("#layer-buildings");
    }
  }
  await waitForWorldReady(page);
  await page.waitForTimeout(4000);

  if (mode === "drag") {
    const box = await page.locator("#cesiumContainer").boundingBox();
    if (box) {
      const before = await page.evaluate(() => ({
        heading: window.viewer?.camera?.heading,
        pitch: window.viewer?.camera?.pitch,
      })).catch(() => null);
      const x = box.x + box.width * 0.5;
      const y = box.y + box.height * 0.5;
      await page.mouse.move(x, y);
      await page.mouse.down();
      await page.mouse.move(x + 180, y + 90, { steps: 24 });
      await page.mouse.up();
      await page.waitForTimeout(6000);
      const after = await page.evaluate(() => ({
        heading: window.viewer?.camera?.heading,
        pitch: window.viewer?.camera?.pitch,
        orbitApplied: window.__orbitDebug?.applied,
      })).catch(() => null);
      if (before && after) {
        if (
          Math.abs((after.heading || 0) - (before.heading || 0)) < 0.0001 &&
          Math.abs((after.pitch || 0) - (before.pitch || 0)) < 0.0001 &&
          !(after.orbitApplied > (before.orbitApplied || 0))
        ) {
          errors.push("drag did not change camera orientation");
        }
      }
    }
  }

  if (mode === "tiles") {
    const weatherTarget = await page.evaluate(() => {
      const container = document.querySelector("#cesiumContainer").getBoundingClientRect();
      const primitives = window.viewer?.scene?.primitives?._primitives || [];
      const offsets = [[0, 0], [2, 0], [-2, 0], [0, 2], [0, -2], [4, 0], [-4, 0], [0, 4], [0, -4]];
      for (const primitive of primitives) {
        if (!(primitive instanceof Cesium.PointPrimitiveCollection)) continue;
        for (let idx = 0; idx < primitive.length; idx += 1) {
          const point = primitive.get(idx);
          if (!point?.id?.uavFeature || point.id.uavFeature.type !== "weather") continue;
          const canvasPos = Cesium.SceneTransforms.worldToWindowCoordinates(window.viewer.scene, point.position);
          if (!canvasPos) continue;
          if (canvasPos.x <= 80 || canvasPos.x >= container.width - 80 || canvasPos.y <= 80 || canvasPos.y >= container.height - 80) continue;
          for (const [dx, dy] of offsets) {
            const pickX = canvasPos.x + dx;
            const pickY = canvasPos.y + dy;
            const picked = window.viewer.scene.pick(new Cesium.Cartesian2(pickX, pickY));
            const pickedId = picked?.id || picked?.primitive?.id;
            if (pickedId?.uavFeature?.type === "weather") {
              return {
                x: container.left + pickX,
                y: container.top + pickY,
                beforeEntities: window.viewer.entities.values.length,
              };
            }
          }
        }
      }
      return null;
    }).catch((error) => ({ error: error.message }));
    if (!weatherTarget || weatherTarget.error) {
      errors.push(`weather sample point is not pickable: ${JSON.stringify(weatherTarget)}`);
    } else {
      await page.mouse.click(weatherTarget.x, weatherTarget.y);
      await page.waitForTimeout(500);
      const weatherSelection = await page.evaluate((beforeEntities) => ({
        detail: document.querySelector("#feature-detail")?.textContent || "",
        beforeEntities,
        afterEntities: window.viewer?.entities?.values?.length || 0,
      }), weatherTarget.beforeEntities).catch((error) => ({ error: error.message, detail: "", beforeEntities: 0, afterEntities: 0 }));
      if (!weatherSelection.detail.includes("天气采样点") || weatherSelection.afterEntities < weatherSelection.beforeEntities + 3) {
        errors.push(`weather click highlight not created: ${JSON.stringify(weatherSelection)}`);
      }
    }

    await page.selectOption("#weather-grid-mode", "medium");
    await page.waitForTimeout(300);
    const mediumWeatherCount = await page.evaluate(() => {
      const primitives = window.viewer?.scene?.primitives?._primitives || [];
      for (const primitive of primitives) {
        if (!(primitive instanceof Cesium.PointPrimitiveCollection)) continue;
        let weatherCount = 0;
        for (let idx = 0; idx < primitive.length; idx += 1) {
          const point = primitive.get(idx);
          if (point?.id?.uavFeature?.type === "weather") weatherCount += 1;
        }
        if (weatherCount > 0) return weatherCount;
      }
      return 0;
    }).catch(() => 0);
    if (mediumWeatherCount !== 75) {
      errors.push(`weather resolution medium mode should render 75 points, got ${mediumWeatherCount}`);
    }
    await page.selectOption("#weather-grid-mode", "full");
    await page.selectOption("#weather-altitude-mode", "all");
    await page.selectOption("#altitude-filter", "all");
    await page.waitForTimeout(300);

    const lightingState = await page.evaluate(() => {
      const select = document.querySelector("#lighting-mode");
      select.value = "sun";
      select.dispatchEvent(new Event("change", { bubbles: true }));
      return {
        viewerShadows: Boolean(window.viewer?.shadows),
        shadowMapEnabled: Boolean(window.viewer?.shadowMap?.enabled),
        ambientOcclusionEnabled: Boolean(window.viewer?.scene?.postProcessStages?.ambientOcclusion?.enabled),
        primitiveShadowModes: (window.viewer?.scene?.primitives?._primitives || [])
          .filter((primitive) => "shadows" in primitive)
          .map((primitive) => primitive.shadows),
        castOnly: Cesium.ShadowMode?.CAST_ONLY,
        receiveOnly: Cesium.ShadowMode?.RECEIVE_ONLY,
      };
    }).catch((error) => ({ error: error.message }));
    if (!lightingState.viewerShadows || !lightingState.shadowMapEnabled) {
      errors.push(`shadow map should be enabled in sun projection mode: ${JSON.stringify(lightingState)}`);
    }
    if (
      !lightingState.primitiveShadowModes?.includes(lightingState.castOnly) ||
      !lightingState.primitiveShadowModes?.includes(lightingState.receiveOnly)
    ) {
      errors.push(`local tiles should include CAST_ONLY buildings and RECEIVE_ONLY ground: ${JSON.stringify(lightingState)}`);
    }
  }

  const status = await page.textContent("#load-status").catch(() => "NO_STATUS");
  const bodyText = await page.textContent("body").catch(() => "");
  await page.screenshot({ path: path.join(OUTPUT_DIR, `uav_web_${mode}.png`), fullPage: false });
  await browser.close();
  return {
    mode,
    status,
    hasRenderingStopped: bodyText.includes("Rendering has stopped"),
    errors: relevantErrors(errors),
  };
}

(async () => {
  const results = [await check("default"), await check("safe"), await check("tiles"), await check("drag")];
  console.log(JSON.stringify(results, null, 2));
  const failed = results.some((item) => item.status !== "世界已加载" || item.hasRenderingStopped || item.errors.length);
  process.exit(failed ? 1 : 0);
})();
