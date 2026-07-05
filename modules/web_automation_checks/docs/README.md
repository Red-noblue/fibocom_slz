# Web 自动化检查模块

本模块用于存放项目级非人工浏览器检查能力。

当前能力：

- 使用 Playwright Chromium 启动真实浏览器。
- 打开目标 Web 页面。
- 捕获 console error、pageerror、requestfailed。
- 检查 Cesium `Rendering has stopped`。
- 将检查截图保存到项目内 `modules/uav_virtual_validation/outputs/automation_checks/`。
- 可扩展到其它 Web 子项目。

运行 UAV 控制台检查：

```bash
cd modules/web_automation_checks
npm install
npx playwright install chromium
npm run check:uav
```

Chromium 由 Playwright 管理，默认缓存位置在用户目录：

```text
~/.cache/ms-playwright/
```
