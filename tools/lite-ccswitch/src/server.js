/**
 * 轻量版 CC Switch 服务器入口。
 *
 * 目标：在无桌面环境的服务器上提供 OpenAI/Codex 兼容本地代理、故障转移、
 * 熔断器和中文网页管理界面。实现参考 cc-switch 的队列路由、熔断和流式
 * 首包探测策略，但移除 Tauri 托盘、桌面接管和本机配置改写能力。
 */

import http from "node:http";
import { createReadStream } from "node:fs";
import {
  mkdir,
  readFile,
  rename,
  stat,
  unlink,
  writeFile,
} from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import crypto from "node:crypto";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DATA_DIR = path.join(__dirname, "data");
const PUBLIC_DIR = path.join(__dirname, "public");
const CONFIG_PATH = process.env.LITE_CCSWITCH_CONFIG || path.join(DATA_DIR, "config.json");
const USAGE_PATH = process.env.LITE_CCSWITCH_USAGE || path.join(DATA_DIR, "usage.jsonl");

const LISTEN_HOST = process.env.LITE_CCSWITCH_HOST || "0.0.0.0";
const LISTEN_PORT = Number(process.env.LITE_CCSWITCH_PORT || "15721");
const PROXY_TOKEN = process.env.LITE_CCSWITCH_PROXY_TOKEN || "";

const MAX_BODY_BYTES = 200 * 1024 * 1024;
const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
]);
const NON_RETRYABLE_STATUS = new Set([400, 405, 406, 413, 414, 415, 422, 501]);
const GPT_55_BILLING_MODEL = "gpt-5.5";
const FAST_MODE_MULTIPLIER = 2.5;
const PROVIDER_TEST_MODEL = "gpt-5.5";
const PROVIDER_TEST_MODELS = ["gpt-5.4-mini", "gpt-5.4", "gpt-5.5"];
const PROVIDER_TEST_EXPECTED_TEXT = "CCOK";
const PROVIDER_TEST_TIMEOUT_MS = 45_000;
const DEFAULT_GPT_55_PRICING = {
  inputPerMillion: 5,
  outputPerMillion: 30,
  cacheReadPerMillion: 0.5,
  cacheCreationPerMillion: 0,
};

const defaultConfig = {
  version: 1,
  proxy: {
    autoFailoverEnabled: true,
    currentProviderId: null,
    maxAttempts: 3,
    streamingFirstByteTimeoutMs: 60_000,
    streamingIdleTimeoutMs: 120_000,
    nonStreamingTimeoutMs: 600_000,
    circuit: {
      failureThreshold: 4,
      successThreshold: 2,
      openTimeoutMs: 60_000,
      errorRateThreshold: 0.6,
      minRequests: 10,
    },
  },
  providers: [],
  billing: {
    currency: "USD",
    pricing: {
      [GPT_55_BILLING_MODEL]: DEFAULT_GPT_55_PRICING,
    },
  },
};

const metrics = {
  startedAt: new Date().toISOString(),
  activeConnections: 0,
  totalRequests: 0,
  successRequests: 0,
  failedRequests: 0,
  failoverCount: 0,
  lastRequestAt: null,
  lastError: null,
  currentProviderId: null,
  currentProviderName: null,
};

let config = structuredClone(defaultConfig);
const breakers = new Map();
const usageState = {
  loaded: false,
  records: [],
  maxRecords: 5000,
};
const resourceSampler = {
  lastCpuUsage: process.cpuUsage(),
  lastHrtimeNs: process.hrtime.bigint(),
  lastCpuPercent: 0,
  lastSampledAtMs: 0,
  cachedPayload: null,
};

class CircuitBreaker {
  constructor(providerId, breakerConfig) {
    this.providerId = providerId;
    this.updateConfig(breakerConfig);
    this.state = "closed";
    this.consecutiveFailures = 0;
    this.consecutiveSuccesses = 0;
    this.totalRequests = 0;
    this.failedRequests = 0;
    this.lastOpenedAt = null;
    this.halfOpenInFlight = 0;
  }

  updateConfig(breakerConfig) {
    this.config = {
      failureThreshold: positiveInt(breakerConfig?.failureThreshold, 4),
      successThreshold: positiveInt(breakerConfig?.successThreshold, 2),
      openTimeoutMs: positiveInt(breakerConfig?.openTimeoutMs, 60_000),
      errorRateThreshold: clampNumber(breakerConfig?.errorRateThreshold, 0.6, 0, 1),
      minRequests: positiveInt(breakerConfig?.minRequests, 10),
    };
  }

  isAvailable() {
    if (this.state === "closed" || this.state === "half_open") {
      return true;
    }
    if (!this.lastOpenedAt) {
      return false;
    }
    if (Date.now() - this.lastOpenedAt >= this.config.openTimeoutMs) {
      this.transitionToHalfOpen();
      return true;
    }
    return false;
  }

  allowRequest() {
    if (this.state === "closed") {
      return { allowed: true, usedHalfOpenPermit: false };
    }
    if (this.state === "open") {
      if (this.isAvailable()) {
        return this.allowHalfOpenProbe();
      }
      return { allowed: false, usedHalfOpenPermit: false };
    }
    return this.allowHalfOpenProbe();
  }

  allowHalfOpenProbe() {
    if (this.halfOpenInFlight > 0) {
      return { allowed: false, usedHalfOpenPermit: false };
    }
    this.halfOpenInFlight += 1;
    return { allowed: true, usedHalfOpenPermit: true };
  }

  releaseHalfOpenPermit(usedHalfOpenPermit) {
    if (usedHalfOpenPermit) {
      this.halfOpenInFlight = Math.max(0, this.halfOpenInFlight - 1);
    }
  }

  recordSuccess(usedHalfOpenPermit) {
    this.releaseHalfOpenPermit(usedHalfOpenPermit);
    this.consecutiveFailures = 0;
    this.totalRequests += 1;
    if (this.state === "half_open") {
      this.consecutiveSuccesses += 1;
      if (this.consecutiveSuccesses >= this.config.successThreshold) {
        this.transitionToClosed();
      }
    }
  }

  recordFailure(usedHalfOpenPermit) {
    this.releaseHalfOpenPermit(usedHalfOpenPermit);
    this.consecutiveFailures += 1;
    this.consecutiveSuccesses = 0;
    this.totalRequests += 1;
    this.failedRequests += 1;

    if (this.state === "half_open") {
      this.transitionToOpen();
      return;
    }

    if (this.state === "closed") {
      const errorRate = this.failedRequests / Math.max(1, this.totalRequests);
      const hitConsecutiveThreshold =
        this.consecutiveFailures >= this.config.failureThreshold;
      const hitErrorRateThreshold =
        this.totalRequests >= this.config.minRequests &&
        errorRate >= this.config.errorRateThreshold;
      if (hitConsecutiveThreshold || hitErrorRateThreshold) {
        this.transitionToOpen();
      }
    }
  }

  reset() {
    this.state = "closed";
    this.consecutiveFailures = 0;
    this.consecutiveSuccesses = 0;
    this.totalRequests = 0;
    this.failedRequests = 0;
    this.lastOpenedAt = null;
    this.halfOpenInFlight = 0;
  }

  transitionToClosed() {
    this.state = "closed";
    this.consecutiveFailures = 0;
    this.consecutiveSuccesses = 0;
    this.lastOpenedAt = null;
    this.halfOpenInFlight = 0;
  }

  transitionToOpen() {
    this.state = "open";
    this.lastOpenedAt = Date.now();
    this.halfOpenInFlight = 0;
  }

  transitionToHalfOpen() {
    this.state = "half_open";
    this.consecutiveSuccesses = 0;
    this.halfOpenInFlight = 0;
  }

  stats() {
    return {
      state: this.state,
      consecutiveFailures: this.consecutiveFailures,
      consecutiveSuccesses: this.consecutiveSuccesses,
      totalRequests: this.totalRequests,
      failedRequests: this.failedRequests,
      errorRate: this.totalRequests > 0 ? this.failedRequests / this.totalRequests : 0,
      lastOpenedAt: this.lastOpenedAt
        ? new Date(this.lastOpenedAt).toISOString()
        : null,
      halfOpenInFlight: this.halfOpenInFlight,
    };
  }
}

await bootstrap();

async function bootstrap() {
  await mkdir(DATA_DIR, { recursive: true });
  config = await loadConfig();
  await loadUsageRecords();
  const server = http.createServer(routeRequest);
  server.requestTimeout = 0;
  server.headersTimeout = 65_000;
  server.listen(LISTEN_PORT, LISTEN_HOST, () => {
    console.log(`lite-ccswitch 代理服务已启动: http://${LISTEN_HOST}:${LISTEN_PORT}`);
    if (LISTEN_HOST === "0.0.0.0") {
      console.log(`局域网访问地址示例: http://<本机局域网IP>:${LISTEN_PORT}`);
    }
  });
}

async function routeRequest(req, res) {
  const url = parseUrl(req);
  try {
    if (url.pathname.startsWith("/api/")) {
      if (!assertAdminAccess(req, res)) {
        return;
      }
      await handleAdminApi(req, res, url);
      return;
    }

    if (isProxyRoute(url.pathname)) {
      if (!assertProxyAccess(req, res)) {
        return;
      }
      await handleProxyRequest(req, res, url);
      return;
    }

    await serveStatic(req, res, url);
  } catch (error) {
    console.error("请求处理失败:", error);
    if (!res.headersSent) {
      sendJson(res, 500, {
        error: {
          message: error instanceof Error ? error.message : String(error),
          type: "internal_error",
        },
      });
    } else {
      res.destroy(error);
    }
  }
}

async function handleAdminApi(req, res, url) {
  const method = req.method || "GET";
  const parts = url.pathname.split("/").filter(Boolean);

  if (method === "GET" && url.pathname === "/api/status") {
    sendJson(res, 200, buildStatusPayload());
    return;
  }

  if (method === "GET" && url.pathname === "/api/config") {
    sendJson(res, 200, sanitizeConfig(config));
    return;
  }

  if (method === "GET" && url.pathname === "/api/billing/summary") {
    sendJson(res, 200, buildBillingSummary({
      startAt: url.searchParams.get("startAt"),
      endAt: url.searchParams.get("endAt"),
    }));
    return;
  }

  if (method === "GET" && url.pathname === "/api/billing/logs") {
    const limit = clampNumber(url.searchParams.get("limit"), 100, 1, 1000);
    sendJson(res, 200, {
      records: usageState.records.slice(-limit).reverse().map(normalizeUsageRecord),
    });
    return;
  }

  if (method === "GET" && url.pathname === "/api/billing/pricing") {
    sendJson(res, 200, sanitizeBillingConfig(config.billing));
    return;
  }

  if (method === "PUT" && url.pathname === "/api/billing/pricing") {
    const payload = await readJsonBody(req);
    updateBillingConfig(payload);
    await saveConfig(config);
    sendJson(res, 200, sanitizeBillingConfig(config.billing));
    return;
  }

  if (method === "PUT" && url.pathname === "/api/config") {
    const payload = await readJsonBody(req);
    updateProxyConfig(payload?.proxy || payload || {});
    await saveConfig(config);
    sendJson(res, 200, sanitizeConfig(config));
    return;
  }

  if (method === "GET" && url.pathname === "/api/providers") {
    sendJson(res, 200, config.providers.map(sanitizeProvider));
    return;
  }

  if (method === "POST" && url.pathname === "/api/providers") {
    const payload = await readJsonBody(req);
    const provider = createProvider(payload);
    config.providers.push(provider);
    if (!config.proxy.currentProviderId) {
      config.proxy.currentProviderId = provider.id;
    }
    await saveConfig(config);
    sendJson(res, 201, sanitizeProvider(provider));
    return;
  }

  if (parts[0] === "api" && parts[1] === "providers" && parts[2]) {
    const providerId = decodeURIComponent(parts[2]);
    const provider = findProvider(providerId);
    if (!provider) {
      sendJson(res, 404, { error: { message: "供应商不存在", type: "not_found" } });
      return;
    }

    if (method === "GET" && parts.length === 3) {
      sendJson(res, 200, provider);
      return;
    }

    if (method === "PUT" && parts.length === 3) {
      const payload = await readJsonBody(req);
      updateProvider(provider, payload);
      await saveConfig(config);
      sendJson(res, 200, sanitizeProvider(provider));
      return;
    }

    if (method === "DELETE" && parts.length === 3) {
      config.providers = config.providers.filter((item) => item.id !== providerId);
      breakers.delete(providerId);
      if (config.proxy.currentProviderId === providerId) {
        const fallback = config.providers.find((item) => item.enabled);
        config.proxy.currentProviderId = fallback?.id || null;
      }
      await saveConfig(config);
      sendJson(res, 200, { ok: true });
      return;
    }

    if (method === "POST" && parts[3] === "reset") {
      getBreaker(provider).reset();
      sendJson(res, 200, { ok: true, circuit: getBreaker(provider).stats() });
      return;
    }

    if (method === "POST" && parts[3] === "select") {
      config.proxy.currentProviderId = provider.id;
      metrics.currentProviderId = provider.id;
      metrics.currentProviderName = provider.name;
      await saveConfig(config);
      sendJson(res, 200, sanitizeConfig(config));
      return;
    }

    if (method === "POST" && parts[3] === "test") {
      const result = await testProvider(provider);
      if (result.ok) {
        getBreaker(provider).reset();
        if (shouldPromoteProviderAfterTest(provider)) {
          config.proxy.currentProviderId = provider.id;
          metrics.currentProviderId = provider.id;
          metrics.currentProviderName = provider.name;
          await saveConfig(config);
        }
      }
      sendJson(res, 200, result);
      return;
    }
  }

  if (method === "PUT" && url.pathname === "/api/failover/queue") {
    const payload = await readJsonBody(req);
    const ids = Array.isArray(payload?.ids) ? payload.ids.map(String) : [];
    const order = new Map(ids.map((id, index) => [id, index + 1]));
    for (const provider of config.providers) {
      provider.inFailoverQueue = order.has(provider.id);
      if (order.has(provider.id)) {
        provider.sortIndex = order.get(provider.id);
      }
    }
    sortProviders();
    await saveConfig(config);
    sendJson(res, 200, config.providers.map(sanitizeProvider));
    return;
  }

  sendJson(res, 404, { error: { message: "管理接口不存在", type: "not_found" } });
}

async function handleProxyRequest(req, res, url) {
  metrics.activeConnections += 1;
  metrics.totalRequests += 1;
  metrics.lastRequestAt = new Date().toISOString();
  const requestStartedAt = Date.now();
  let requestModel = null;
  let selectedProvider = null;
  let finalStatusCode = 0;
  let finalError = null;

  try {
    const body = await readRawBody(req);
    requestModel = extractRequestModel(body);
    const providers = selectProviders();
    if (providers.length === 0) {
      metrics.failedRequests += 1;
      finalStatusCode = 503;
      finalError = "没有可用供应商，请先在网页中添加并启用供应商。";
      sendJson(res, 503, {
        error: {
          message: finalError,
          type: "no_available_provider",
        },
      });
      return;
    }

    const maxAttempts = Math.min(
      providers.length,
      positiveInt(config.proxy.maxAttempts, 3),
    );
    let lastError = null;
    let attempted = 0;

    for (const provider of providers) {
      if (attempted >= maxAttempts) {
        break;
      }

      const breaker = getBreaker(provider);
      const permit = providers.length === 1
        ? { allowed: true, usedHalfOpenPermit: false }
        : breaker.allowRequest();

      if (!permit.allowed) {
        continue;
      }

      attempted += 1;
      metrics.currentProviderId = provider.id;
      metrics.currentProviderName = provider.name;
      selectedProvider = provider;

      try {
        const result = await forwardToProvider(req, url, body, provider);
        finalStatusCode = result.status;
        await writeProviderResponse(res, result, req, provider, {
          startedAt: requestStartedAt,
          requestModel,
          endpoint: normalizeProxyPath(url.pathname),
        });
        breaker.recordSuccess(permit.usedHalfOpenPermit);
        config.proxy.currentProviderId = provider.id;
        if (attempted > 1) {
          metrics.failoverCount += 1;
        }
        metrics.successRequests += 1;
        metrics.lastError = null;
        await maybeSaveCurrentProvider(provider.id);
        return;
      } catch (error) {
        lastError = error;
        if (error.retryable) {
          breaker.recordFailure(permit.usedHalfOpenPermit);
          metrics.lastError = `${provider.name}: ${error.message}`;
          if (res.headersSent) {
            throw error;
          }
          continue;
        }
        breaker.releaseHalfOpenPermit(permit.usedHalfOpenPermit);
        throw error;
      }
    }

    metrics.failedRequests += 1;
    const message = lastError?.message || "所有供应商均不可用";
    metrics.lastError = message;
    finalStatusCode = lastError?.status || 503;
    finalError = message;
    sendJson(res, lastError?.status || 503, {
      error: {
        message,
        type: "failover_exhausted",
        attempted,
      },
    });
  } catch (error) {
    metrics.failedRequests += 1;
    metrics.lastError = error instanceof Error ? error.message : String(error);
    finalStatusCode = error.status || 502;
    finalError = metrics.lastError;
    if (!res.headersSent) {
      sendJson(res, error.status || 502, {
        error: {
          message: metrics.lastError,
          type: error.retryable ? "retryable_proxy_error" : "proxy_error",
        },
      });
    } else {
      res.destroy(error);
    }
  } finally {
    if (finalError) {
      await recordUsage({
        provider: selectedProvider,
        endpoint: normalizeProxyPath(url.pathname),
        requestModel,
        statusCode: finalStatusCode || 502,
        latencyMs: Date.now() - requestStartedAt,
        isStreaming: false,
        error: finalError,
      });
    }
    metrics.activeConnections = Math.max(0, metrics.activeConnections - 1);
  }
}

async function forwardToProvider(clientReq, url, originalBody, provider) {
  const requestPath = normalizeProxyPath(url.pathname);
  const targetUrl = joinUpstreamUrl(provider.baseUrl, requestPath, url.search);
  const isStreaming = isStreamingRequest(clientReq, requestPath, originalBody);
  const body = rectifyRequestBody(provider, originalBody);
  const headers = buildUpstreamHeaders(clientReq, provider);
  const controller = new AbortController();
  const firstByteTimeout = positiveInt(
    config.proxy.streamingFirstByteTimeoutMs,
    60_000,
  );
  const nonStreamingTimeout = positiveInt(
    config.proxy.nonStreamingTimeoutMs,
    600_000,
  );
  const headerTimeout = isStreaming ? firstByteTimeout : nonStreamingTimeout;

  let headerTimer = setTimeout(() => controller.abort(), headerTimeout);
  let response;
  try {
    response = await fetch(targetUrl, {
      method: clientReq.method,
      headers,
      body: shouldSendBody(clientReq.method) ? body : undefined,
      signal: controller.signal,
    });
  } catch (error) {
    throw retryableError(`连接上游失败: ${formatFetchError(error)}`);
  } finally {
    clearTimeout(headerTimer);
  }

  if (!response.ok) {
    const text = await safeReadErrorBody(response);
    const retryable = isRetryableStatus(response.status);
    throw upstreamError(response.status, text, retryable);
  }

  if (isStreaming) {
    if (!response.body) {
      throw retryableError("上游没有返回可读流");
    }
    const reader = response.body.getReader();
    const firstChunk = await readFirstChunk(reader, firstByteTimeout, controller);
    const firstChunkError = detectUpstreamPayloadError(Buffer.from(firstChunk).toString("utf8"));
    if (firstChunkError) {
      controller.abort();
      throw upstreamError(
        firstChunkError.status,
        firstChunkError.message,
        firstChunkError.retryable,
      );
    }
    return {
      mode: "stream",
      status: response.status,
      headers: response.headers,
      firstChunk,
      reader,
      controller,
      requestBody: body,
    };
  }

  const bodyTimer = setTimeout(() => controller.abort(), nonStreamingTimeout);
  try {
    const buffer = Buffer.from(await response.arrayBuffer());
    const payloadError = detectUpstreamPayloadError(buffer.toString("utf8"));
    if (payloadError) {
      throw upstreamError(payloadError.status, payloadError.message, payloadError.retryable);
    }
    return {
      mode: "buffer",
      status: response.status,
      headers: response.headers,
      body: buffer,
      requestBody: body,
    };
  } catch (error) {
    if (error?.status || error?.retryable !== undefined) {
      throw error;
    }
    throw retryableError(`读取上游响应失败: ${formatFetchError(error)}`);
  } finally {
    clearTimeout(bodyTimer);
  }
}

async function writeProviderResponse(res, result, clientReq, provider, usageContext) {
  copyResponseHeaders(res, result.headers, result.mode);
  res.statusCode = result.status;
  res.setHeader("x-lite-ccswitch-provider-id", provider.id);
  res.setHeader("x-lite-ccswitch-provider-name", encodeURIComponent(provider.name));

  if (result.mode === "buffer") {
    res.end(result.body);
    await recordUsage({
      provider,
      endpoint: usageContext.endpoint,
      requestModel: usageContext.requestModel,
      statusCode: result.status,
      latencyMs: Date.now() - usageContext.startedAt,
      isStreaming: false,
      responseBody: result.body,
      requestBody: result.requestBody,
    });
    return;
  }

  res.write(Buffer.from(result.firstChunk));
  const streamText = await pipeReadableStream(
    res,
    result.reader,
    result.controller,
    result.firstChunk,
  );
  await recordUsage({
    provider,
    endpoint: usageContext.endpoint,
    requestModel: usageContext.requestModel,
    statusCode: result.status,
    latencyMs: Date.now() - usageContext.startedAt,
    isStreaming: true,
    responseText: streamText,
    requestBody: result.requestBody,
  });
}

async function pipeReadableStream(res, reader, controller, firstChunk) {
  const idleTimeout = Number(config.proxy.streamingIdleTimeoutMs || 0);
  let completed = false;
  const abortOnClose = () => {
    if (!completed) {
      controller.abort();
    }
  };
  const usageChunks = [Buffer.from(firstChunk || []).toString("utf8")];
  res.on("close", abortOnClose);

  try {
    while (!res.destroyed) {
      const chunk = await readNextChunk(reader, idleTimeout, controller);
      if (chunk.done) {
        completed = true;
        res.end();
        return usageChunks.join("").slice(-200_000);
      }
      const buffer = Buffer.from(chunk.value);
      usageChunks.push(buffer.toString("utf8"));
      if (usageChunks.join("").length > 200_000) {
        usageChunks.splice(0, Math.max(1, usageChunks.length - 8));
      }
      if (!res.write(buffer)) {
        await onceDrain(res);
      }
    }
    throw retryableError("流式响应在完成前关闭");
  } catch (error) {
    const message = `流式响应中断: ${formatFetchError(error)}`;
    metrics.lastError = message;
    if (!res.destroyed) {
      res.destroy(error);
    }
    throw retryableError(message);
  } finally {
    res.off("close", abortOnClose);
  }
}

function buildStatusPayload() {
  const uptimeSeconds = Math.floor(
    (Date.now() - new Date(metrics.startedAt).getTime()) / 1000,
  );
  const successRate =
    metrics.totalRequests > 0
      ? (metrics.successRequests / metrics.totalRequests) * 100
      : 0;
  const statusProvider = getStatusCurrentProvider();

  return {
    running: true,
    address: LISTEN_HOST,
    port: LISTEN_PORT,
    uptimeSeconds,
    activeConnections: metrics.activeConnections,
    totalRequests: metrics.totalRequests,
    successRequests: metrics.successRequests,
    failedRequests: metrics.failedRequests,
    successRate,
    failoverCount: metrics.failoverCount,
    lastRequestAt: metrics.lastRequestAt,
    lastError: metrics.lastError,
    currentProviderId: statusProvider?.id || null,
    currentProviderName: statusProvider?.name || null,
    providers: config.providers.map((provider) => ({
      ...sanitizeProvider(provider),
      circuit: getBreaker(provider).stats(),
    })),
    proxy: sanitizeConfig(config).proxy,
    resources: buildResourcePayload(),
  };
}

function buildResourcePayload() {
  const now = Date.now();
  if (resourceSampler.cachedPayload && now - resourceSampler.lastSampledAtMs < 30_000) {
    return resourceSampler.cachedPayload;
  }

  const memory = process.memoryUsage();
  const nextCpuUsage = process.cpuUsage();
  const nextHrtimeNs = process.hrtime.bigint();
  const elapsedUs = Number(nextHrtimeNs - resourceSampler.lastHrtimeNs) / 1000;
  const cpuDeltaUs =
    nextCpuUsage.user +
    nextCpuUsage.system -
    resourceSampler.lastCpuUsage.user -
    resourceSampler.lastCpuUsage.system;

  if (elapsedUs > 0) {
    resourceSampler.lastCpuPercent = Math.max(0, (cpuDeltaUs / elapsedUs) * 100);
    resourceSampler.lastCpuUsage = nextCpuUsage;
    resourceSampler.lastHrtimeNs = nextHrtimeNs;
  }

  const payload = {
    sampledAt: new Date().toISOString(),
    pid: process.pid,
    uptimeSeconds: Math.floor(process.uptime()),
    cpuPercent: roundNumber(resourceSampler.lastCpuPercent, 1),
    memory: {
      rssBytes: memory.rss,
      heapUsedBytes: memory.heapUsed,
      heapTotalBytes: memory.heapTotal,
      externalBytes: memory.external,
      rssMb: bytesToMb(memory.rss),
      heapUsedMb: bytesToMb(memory.heapUsed),
      heapTotalMb: bytesToMb(memory.heapTotal),
      externalMb: bytesToMb(memory.external),
    },
  };
  resourceSampler.cachedPayload = payload;
  resourceSampler.lastSampledAtMs = now;
  return payload;
}

function getStatusCurrentProvider() {
  const enabled = config.providers.filter((provider) => provider.enabled && provider.baseUrl);
  if (!enabled.length) return null;
  if (!config.proxy.autoFailoverEnabled) {
    return enabled.find((provider) => provider.id === config.proxy.currentProviderId) || enabled[0];
  }
  const queued = enabled
    .filter((provider) => provider.inFailoverQueue)
    .sort(compareProviders);
  const candidates = queued.length ? queued : enabled.sort(compareProviders);
  return candidates.find((provider) => getBreaker(provider).stats().state !== "open") ||
    candidates[0] ||
    null;
}

async function loadUsageRecords() {
  try {
    const raw = await readFile(USAGE_PATH, "utf8");
    usageState.records = raw
      .split("\n")
      .filter(Boolean)
      .map((line) => JSON.parse(line))
      .slice(-usageState.maxRecords);
  } catch (error) {
    if (error?.code !== "ENOENT") {
      console.warn(`读取计费日志失败，已从空日志启动: ${error.message}`);
    }
    usageState.records = [];
  }
  usageState.loaded = true;
}

async function recordUsage(input) {
  if (!usageState.loaded) {
    await loadUsageRecords();
  }
  const usage = extractUsage(input.responseBody, input.responseText);
  const requestModel = input.requestModel || extractRequestModel(input.requestBody);
  const responseModel = usage.model || requestModel || "unknown";
  const billingModel = normalizeBillingModel(responseModel);
  const billingMode = detectFastBillingMode(input.requestBody, input.responseBody, input.responseText)
    ? "fast"
    : "standard";
  const billingMultiplier = billingMode === "fast" ? FAST_MODE_MULTIPLIER : 1;
  const baseCost = estimateCost(billingModel, usage);
  const cost = roundMoney(baseCost * billingMultiplier);
  const record = {
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    providerId: input.provider?.id || null,
    providerName: input.provider?.name || "未选择",
    endpoint: input.endpoint || "",
    requestModel: requestModel || "",
    responseModel,
    billingModel,
    billingMode,
    billingMultiplier,
    statusCode: Number(input.statusCode || 0),
    latencyMs: Number(input.latencyMs || 0),
    isStreaming: Boolean(input.isStreaming),
    inputTokens: usage.inputTokens,
    outputTokens: usage.outputTokens,
    cacheReadTokens: usage.cacheReadTokens,
    cacheCreationTokens: usage.cacheCreationTokens,
    totalTokens: usage.totalTokens,
    baseEstimatedCostUsd: baseCost,
    estimatedCostUsd: cost,
    error: input.error || "",
  };
  usageState.records.push(record);
  usageState.records = usageState.records.slice(-usageState.maxRecords);
  await mkdir(path.dirname(USAGE_PATH), { recursive: true });
  await writeFile(USAGE_PATH, `${usageState.records.map(JSON.stringify).join("\n")}\n`, "utf8");
}

function buildBillingSummary(filters = {}) {
  const startMs = parseOptionalTime(filters.startAt);
  const endMs = parseOptionalTime(filters.endAt);
  const summary = {
    totalRequests: usageState.records.length,
    successRequests: 0,
    failedRequests: 0,
    inputTokens: 0,
    outputTokens: 0,
    cacheReadTokens: 0,
    cacheCreationTokens: 0,
    totalTokens: 0,
    estimatedCostUsd: 0,
    providers: {},
    models: {},
    pricing: sanitizeBillingConfig(config.billing),
  };

  for (const record of usageState.records) {
    const timestampMs = Date.parse(record.timestamp || "");
    if (startMs !== null && (!Number.isFinite(timestampMs) || timestampMs < startMs)) continue;
    if (endMs !== null && (!Number.isFinite(timestampMs) || timestampMs > endMs)) continue;
    const normalizedRecord = normalizeUsageRecord(record);
    const ok = normalizedRecord.statusCode >= 200 && normalizedRecord.statusCode < 400 && !normalizedRecord.error;
    if (ok) summary.successRequests += 1;
    else summary.failedRequests += 1;
    addUsageTotals(summary, normalizedRecord);

    const providerKey = normalizedRecord.providerName || normalizedRecord.providerId || "未选择";
    summary.providers[providerKey] ??= emptyUsageBucket(providerKey);
    addUsageTotals(summary.providers[providerKey], normalizedRecord);
    summary.providers[providerKey].requests += 1;

    const modelKey = normalizedRecord.billingModel || normalizedRecord.responseModel || normalizedRecord.requestModel || "unknown";
    summary.models[modelKey] ??= emptyUsageBucket(modelKey);
    addUsageTotals(summary.models[modelKey], normalizedRecord);
    summary.models[modelKey].requests += 1;
  }

  return {
    ...summary,
    providers: Object.values(summary.providers).sort(compareUsageBuckets),
    models: Object.values(summary.models).sort(compareUsageBuckets),
  };
}

function parseOptionalTime(value) {
  if (!value) return null;
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

function normalizeUsageRecord(record) {
  const responseModel = record.responseModel || record.requestModel || "unknown";
  const billingModel = record.billingModel || normalizeBillingModel(responseModel);
  const billingMode = record.billingMode || (Number(record.billingMultiplier || 1) > 1 ? "fast" : "standard");
  const billingMultiplier = billingMode === "fast"
    ? Number(record.billingMultiplier || FAST_MODE_MULTIPLIER)
    : 1;
  const usage = {
    inputTokens: Number(record.inputTokens || 0),
    outputTokens: Number(record.outputTokens || 0),
    cacheReadTokens: Number(record.cacheReadTokens || 0),
    cacheCreationTokens: Number(record.cacheCreationTokens || 0),
  };
  const baseEstimatedCostUsd = estimateCost(billingModel, usage);
  return {
    ...record,
    responseModel,
    billingModel,
    billingMode,
    billingMultiplier,
    baseEstimatedCostUsd,
    estimatedCostUsd: roundMoney(baseEstimatedCostUsd * billingMultiplier),
  };
}

function emptyUsageBucket(name) {
  return {
    name,
    requests: 0,
    inputTokens: 0,
    outputTokens: 0,
    cacheReadTokens: 0,
    cacheCreationTokens: 0,
    totalTokens: 0,
    estimatedCostUsd: 0,
  };
}

function addUsageTotals(target, record) {
  target.inputTokens += Number(record.inputTokens || 0);
  target.outputTokens += Number(record.outputTokens || 0);
  target.cacheReadTokens += Number(record.cacheReadTokens || 0);
  target.cacheCreationTokens += Number(record.cacheCreationTokens || 0);
  target.totalTokens += Number(record.totalTokens || 0);
  target.estimatedCostUsd += Number(record.estimatedCostUsd || 0);
}

function compareUsageBuckets(a, b) {
  return (b.estimatedCostUsd - a.estimatedCostUsd) ||
    (b.totalTokens - a.totalTokens) ||
    String(a.name).localeCompare(String(b.name), "zh-CN");
}

function extractRequestModel(body) {
  if (!body?.length) return "";
  try {
    const json = JSON.parse(Buffer.from(body).toString("utf8"));
    return String(json?.model || "");
  } catch {
    return "";
  }
}

function extractUsage(responseBody, responseText) {
  const usage = {
    model: "",
    inputTokens: 0,
    outputTokens: 0,
    cacheReadTokens: 0,
    cacheCreationTokens: 0,
    totalTokens: 0,
  };
  const candidates = [];

  if (responseBody?.length) {
    try {
      candidates.push(JSON.parse(Buffer.from(responseBody).toString("utf8")));
    } catch {}
  }

  if (responseText) {
    for (const line of String(responseText).split("\n")) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const data = trimmed.slice(5).trim();
      if (!data || data === "[DONE]") continue;
      try {
        candidates.push(JSON.parse(data));
      } catch {}
    }
  }

  for (const item of candidates) {
    mergeUsage(usage, item);
  }
  usage.totalTokens ||= usage.inputTokens + usage.outputTokens;
  return usage;
}

function normalizeBillingModel(model) {
  const value = String(model || "").trim();
  if (!value) return "unknown";
  const normalized = value.toLowerCase();
  if (
    /^gpt-5\.[45](?:$|[-_.:])/.test(normalized) ||
    /^codex-5\.[45](?:$|[-_.:])/.test(normalized) ||
    /^gpt-5[45](?:$|[-_.:])/.test(normalized) ||
    /^codex-5[45](?:$|[-_.:])/.test(normalized)
  ) {
    return GPT_55_BILLING_MODEL;
  }
  return value;
}

function detectFastBillingMode(requestBody, responseBody, responseText) {
  const candidates = [];
  pushJsonCandidate(candidates, requestBody);
  pushJsonCandidate(candidates, responseBody);
  if (responseText) {
    for (const line of String(responseText).split("\n")) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const data = trimmed.slice(5).trim();
      if (!data || data === "[DONE]") continue;
      pushJsonTextCandidate(candidates, data);
    }
  }
  return candidates.some(hasFastBillingSignal);
}

function pushJsonCandidate(candidates, body) {
  if (!body?.length) return;
  pushJsonTextCandidate(candidates, Buffer.from(body).toString("utf8"));
}

function pushJsonTextCandidate(candidates, text) {
  try {
    candidates.push(JSON.parse(text));
  } catch {}
}

function hasFastBillingSignal(payload) {
  if (!payload || typeof payload !== "object") return false;
  if (
    payload.service_tier === "priority" ||
    payload.serviceTier === "priority" ||
    payload.priority === true ||
    payload.fast === true ||
    payload.fastMode === true ||
    payload.fast_mode === true ||
    payload.metadata?.fastMode === true ||
    payload.metadata?.fast_mode === true
  ) {
    return true;
  }
  if (payload.response && typeof payload.response === "object") {
    return hasFastBillingSignal(payload.response);
  }
  return false;
}

function mergeUsage(target, payload) {
  if (!payload || typeof payload !== "object") return;
  if (payload.model && !target.model) {
    target.model = String(payload.model);
  }
  const usage = payload.usage || payload.response?.usage;
  if (!usage || typeof usage !== "object") {
    if (payload.response && typeof payload.response === "object") {
      mergeUsage(target, payload.response);
    }
    return;
  }

  const inputDetails = usage.input_tokens_details || usage.prompt_tokens_details || {};
  const outputDetails = usage.output_tokens_details || usage.completion_tokens_details || {};
  target.inputTokens = Math.max(
    target.inputTokens,
    Number(usage.input_tokens ?? usage.prompt_tokens ?? 0),
  );
  target.outputTokens = Math.max(
    target.outputTokens,
    Number(usage.output_tokens ?? usage.completion_tokens ?? 0),
  );
  target.cacheReadTokens = Math.max(
    target.cacheReadTokens,
    Number(inputDetails.cached_tokens ?? inputDetails.cache_read_tokens ?? 0),
  );
  target.cacheCreationTokens = Math.max(
    target.cacheCreationTokens,
    Number(inputDetails.cache_creation_tokens ?? outputDetails.cache_creation_tokens ?? 0),
  );
  target.totalTokens = Math.max(
    target.totalTokens,
    Number(usage.total_tokens ?? 0),
  );
}

function estimateCost(model, usage) {
  const pricing = getPricingForModel(model);
  if (!pricing) return 0;
  const inputCost = (usage.inputTokens / 1_000_000) * pricing.inputPerMillion;
  const outputCost = (usage.outputTokens / 1_000_000) * pricing.outputPerMillion;
  const cacheReadCost = (usage.cacheReadTokens / 1_000_000) * pricing.cacheReadPerMillion;
  const cacheCreationCost =
    (usage.cacheCreationTokens / 1_000_000) * pricing.cacheCreationPerMillion;
  return roundMoney(inputCost + outputCost + cacheReadCost + cacheCreationCost);
}

function getPricingForModel(model) {
  const pricing = config.billing?.pricing || {};
  const billingModel = normalizeBillingModel(model);
  const exact = pricing[billingModel] || pricing[model];
  const wildcard = pricing["*"];
  return normalizePricing(exact || wildcard);
}

function updateBillingConfig(payload = {}) {
  const pricingPayload = payload.pricing || payload;
  const pricing = normalizePricingTable(defaultConfig.billing.pricing);
  for (const [model, value] of Object.entries(pricingPayload || {})) {
    const normalized = normalizePricing(value);
    if (normalized) {
      pricing[String(model || "").trim() || "*"] = normalized;
    }
  }
  config.billing = {
    currency: "USD",
    pricing,
  };
}

function sanitizeBillingConfig(billing = {}) {
  return {
    currency: "USD",
    pricing: {
      ...normalizePricingTable(defaultConfig.billing.pricing),
      ...normalizePricingTable(billing.pricing),
    },
  };
}

function normalizePricingTable(pricing = {}) {
  const result = {};
  for (const [model, value] of Object.entries(pricing || {})) {
    const normalized = normalizePricing(value);
    if (normalized) {
      result[model] = normalized;
    }
  }
  return result;
}

function normalizePricing(value) {
  if (!value || typeof value !== "object") return null;
  const next = {
    inputPerMillion: nonNegativeNumber(value.inputPerMillion ?? value.input, 0),
    outputPerMillion: nonNegativeNumber(value.outputPerMillion ?? value.output, 0),
    cacheReadPerMillion: nonNegativeNumber(value.cacheReadPerMillion ?? value.cacheRead, 0),
    cacheCreationPerMillion: nonNegativeNumber(
      value.cacheCreationPerMillion ?? value.cacheCreation,
      0,
    ),
  };
  return Object.values(next).some((item) => item > 0) ? next : null;
}

async function loadConfig() {
  try {
    const raw = await readFile(CONFIG_PATH, "utf8");
    const parsed = JSON.parse(raw);
    return normalizeConfig(parsed);
  } catch (error) {
    if (error?.code !== "ENOENT") {
      console.warn(`读取配置失败，已使用默认配置: ${error.message}`);
    }
    const initial = structuredClone(defaultConfig);
    await saveConfig(initial);
    return initial;
  }
}

async function saveConfig(nextConfig) {
  await mkdir(path.dirname(CONFIG_PATH), { recursive: true });
  const tmpPath = `${CONFIG_PATH}.${process.pid}.${Date.now()}.tmp`;
  try {
    await writeFile(tmpPath, `${JSON.stringify(nextConfig, null, 2)}\n`, "utf8");
    await rename(tmpPath, CONFIG_PATH);
  } catch (error) {
    await unlink(tmpPath).catch(() => {});
    throw error;
  }
}

function normalizeConfig(input) {
  const next = structuredClone(defaultConfig);
  next.proxy = {
    ...next.proxy,
    ...(input?.proxy && typeof input.proxy === "object" ? input.proxy : {}),
  };
  next.proxy.circuit = {
    ...defaultConfig.proxy.circuit,
    ...(input?.proxy?.circuit && typeof input.proxy.circuit === "object"
      ? input.proxy.circuit
      : {}),
  };
  next.providers = Array.isArray(input?.providers)
    ? input.providers.map(createProvider).sort(compareProviders)
    : [];
  next.billing = {
    ...defaultConfig.billing,
    ...(input?.billing && typeof input.billing === "object" ? input.billing : {}),
    pricing: {
      ...normalizePricingTable(defaultConfig.billing.pricing),
      ...normalizePricingTable(input?.billing?.pricing),
    },
  };
  if (
    next.proxy.currentProviderId &&
    !next.providers.some((provider) => provider.id === next.proxy.currentProviderId)
  ) {
    next.proxy.currentProviderId = null;
  }
  return next;
}

function updateProxyConfig(payload) {
  config.proxy.autoFailoverEnabled = Boolean(
    payload.autoFailoverEnabled ?? config.proxy.autoFailoverEnabled,
  );
  config.proxy.maxAttempts = positiveInt(payload.maxAttempts, config.proxy.maxAttempts);
  config.proxy.streamingFirstByteTimeoutMs = positiveInt(
    payload.streamingFirstByteTimeoutMs,
    config.proxy.streamingFirstByteTimeoutMs,
  );
  config.proxy.streamingIdleTimeoutMs = Math.max(
    0,
    Number(payload.streamingIdleTimeoutMs ?? config.proxy.streamingIdleTimeoutMs),
  );
  config.proxy.nonStreamingTimeoutMs = positiveInt(
    payload.nonStreamingTimeoutMs,
    config.proxy.nonStreamingTimeoutMs,
  );

  if (payload.circuit && typeof payload.circuit === "object") {
    config.proxy.circuit = {
      failureThreshold: positiveInt(
        payload.circuit.failureThreshold,
        config.proxy.circuit.failureThreshold,
      ),
      successThreshold: positiveInt(
        payload.circuit.successThreshold,
        config.proxy.circuit.successThreshold,
      ),
      openTimeoutMs: positiveInt(
        payload.circuit.openTimeoutMs,
        config.proxy.circuit.openTimeoutMs,
      ),
      errorRateThreshold: clampNumber(
        payload.circuit.errorRateThreshold,
        config.proxy.circuit.errorRateThreshold,
        0,
        1,
      ),
      minRequests: positiveInt(
        payload.circuit.minRequests,
        config.proxy.circuit.minRequests,
      ),
    };
    for (const provider of config.providers) {
      getBreaker(provider).updateConfig(config.proxy.circuit);
    }
  }
}

function createProvider(payload = {}) {
  const id = String(payload.id || crypto.randomUUID());
  return {
    id,
    name: String(payload.name || "未命名供应商"),
    baseUrl: normalizeBaseUrl(payload.baseUrl || payload.base_url || ""),
    apiKey: String(payload.apiKey || payload.api_key || ""),
    enabled: Boolean(payload.enabled ?? true),
    inFailoverQueue: Boolean(payload.inFailoverQueue ?? true),
    sortIndex: positiveInt(payload.sortIndex, config.providers?.length + 1 || 1),
    notes: String(payload.notes || ""),
    modelMap: normalizeObject(payload.modelMap),
    modelSupport: normalizeModelSupport(payload.modelSupport || payload.model_support),
    stripParams: Array.isArray(payload.stripParams)
      ? payload.stripParams.map(String)
      : [],
    customHeaders: normalizeObject(payload.customHeaders),
  };
}

function updateProvider(provider, payload = {}) {
  if (payload.name !== undefined) provider.name = String(payload.name);
  if (payload.baseUrl !== undefined || payload.base_url !== undefined) {
    provider.baseUrl = normalizeBaseUrl(payload.baseUrl || payload.base_url || "");
  }
  if (payload.apiKey !== undefined || payload.api_key !== undefined) {
    const nextKey = payload.apiKey !== undefined ? payload.apiKey : payload.api_key;
    provider.apiKey = String(nextKey ?? "");
  }
  if (payload.enabled !== undefined) provider.enabled = Boolean(payload.enabled);
  if (payload.inFailoverQueue !== undefined) {
    provider.inFailoverQueue = Boolean(payload.inFailoverQueue);
  }
  if (payload.sortIndex !== undefined) {
    provider.sortIndex = positiveInt(payload.sortIndex, provider.sortIndex);
  }
  if (payload.notes !== undefined) provider.notes = String(payload.notes || "");
  if (payload.modelMap !== undefined) provider.modelMap = normalizeObject(payload.modelMap);
  if (payload.modelSupport !== undefined || payload.model_support !== undefined) {
    provider.modelSupport = normalizeModelSupport(payload.modelSupport || payload.model_support);
  }
  if (payload.customHeaders !== undefined) {
    provider.customHeaders = normalizeObject(payload.customHeaders);
  }
  if (payload.stripParams !== undefined) {
    provider.stripParams = Array.isArray(payload.stripParams)
      ? payload.stripParams.map(String)
      : [];
  }
  sortProviders();
}

function sanitizeConfig(rawConfig) {
  return {
    ...rawConfig,
    providers: rawConfig.providers.map(sanitizeProvider),
  };
}

function sanitizeProvider(provider) {
  return {
    id: provider.id,
    name: provider.name,
    baseUrl: provider.baseUrl,
    enabled: provider.enabled,
    inFailoverQueue: provider.inFailoverQueue,
    sortIndex: provider.sortIndex,
    notes: provider.notes,
    hasApiKey: Boolean(provider.apiKey),
    apiKeyMasked: maskSecret(provider.apiKey),
    modelMap: provider.modelMap || {},
    modelSupport: normalizeModelSupport(provider.modelSupport),
    stripParams: provider.stripParams || [],
    customHeaders: maskHeaders(provider.customHeaders || {}),
  };
}

function selectProviders() {
  const enabled = config.providers.filter((provider) => provider.enabled && provider.baseUrl);
  if (!config.proxy.autoFailoverEnabled) {
    const current = enabled.find(
      (provider) => provider.id === config.proxy.currentProviderId,
    );
    return current ? [current] : enabled.slice(0, 1);
  }

  const queued = enabled
    .filter((provider) => provider.inFailoverQueue)
    .sort(compareProviders)
    .filter((provider) => getBreaker(provider).isAvailable());
  return queued.length > 0
    ? queued
    : enabled.sort(compareProviders).filter((provider) => getBreaker(provider).isAvailable());
}

function getBreaker(provider) {
  if (!breakers.has(provider.id)) {
    breakers.set(provider.id, new CircuitBreaker(provider.id, config.proxy.circuit));
  }
  const breaker = breakers.get(provider.id);
  breaker.updateConfig(config.proxy.circuit);
  return breaker;
}

async function maybeSaveCurrentProvider(providerId) {
  if (config.proxy.currentProviderId !== providerId) {
    config.proxy.currentProviderId = providerId;
    await saveConfig(config);
  }
}

function shouldPromoteProviderAfterTest(provider) {
  if (!provider.enabled || !provider.baseUrl) return false;
  if (!config.proxy.autoFailoverEnabled) return true;
  if (!provider.inFailoverQueue) return false;
  const firstQueued = config.providers
    .filter((item) => item.enabled && item.baseUrl && item.inFailoverQueue)
    .sort(compareProviders)[0];
  return firstQueued?.id === provider.id;
}

async function testProvider(provider) {
  const startedAt = Date.now();
  const attempts = [];
  const models = getProviderTestModels(provider);
  for (const requestModel of models) {
    const result = await testProviderWithModel(provider, requestModel, startedAt);
    attempts.push({
      model: requestModel,
      ok: result.ok,
      status: result.status,
      message: result.message,
      latencyMs: result.latencyMs,
    });
    rememberProviderModelTest(provider, requestModel, result);
    await saveConfig(config);
    if (result.ok) {
      return {
        ...result,
        attempts,
        supportedModels: provider.modelSupport?.supportedModels || [],
        unsupportedModels: provider.modelSupport?.unsupportedModels || [],
      };
    }
    if (!shouldTryNextProviderTestModel(result, attempts.length, models.length)) {
      return {
        ...result,
        attempts,
        supportedModels: provider.modelSupport?.supportedModels || [],
        unsupportedModels: provider.modelSupport?.unsupportedModels || [],
      };
    }
  }
  return {
    ok: false,
    status: attempts.at(-1)?.status || 0,
    latencyMs: Date.now() - startedAt,
    model: attempts.at(-1)?.model || PROVIDER_TEST_MODEL,
    message: `所有测试模型均不可用：${attempts.map((item) => `${item.model}(${item.status || "无状态"})`).join(" -> ")}`,
    attempts,
    supportedModels: provider.modelSupport?.supportedModels || [],
    unsupportedModels: provider.modelSupport?.unsupportedModels || [],
  };
}

async function testProviderWithModel(provider, requestModel, startedAt) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), PROVIDER_TEST_TIMEOUT_MS);
  const requestBody = rectifyRequestBody(
    provider,
    Buffer.from(JSON.stringify({
      model: requestModel,
      input: `请只回复 ${PROVIDER_TEST_EXPECTED_TEXT}，不要输出其他内容。`,
      max_output_tokens: 16,
      stream: false,
    })),
  );
  try {
    const url = joinUpstreamUrl(provider.baseUrl, "/v1/responses", "");
    const headers = buildProviderOnlyHeaders(provider);
    headers.set("content-type", "application/json");
    headers.set("accept", "application/json");
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: requestBody,
      signal: controller.signal,
    });
    const latencyMs = Date.now() - startedAt;
    const responseBody = Buffer.from(await response.arrayBuffer());
    await recordUsage({
      provider,
      endpoint: "/v1/responses#provider-test",
      requestModel,
      statusCode: response.status,
      latencyMs,
      isStreaming: false,
      responseBody,
      requestBody,
    });
    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        latencyMs,
        model: requestModel,
        message: safeTextFromBuffer(responseBody) || `HTTP ${response.status}`,
      };
    }

    const answer = extractProviderTestAnswer(responseBody);
    const ok = isProviderTestAnswerOk(answer);
    return {
      ok,
      status: response.status,
      latencyMs,
      model: requestModel,
      answer: truncateText(answer, 200),
      expected: PROVIDER_TEST_EXPECTED_TEXT,
      message: ok
        ? `模型回答正常: ${truncateText(answer, 80)}`
        : `模型回答不符合预期: ${truncateText(answer || safeTextFromBuffer(responseBody), 200) || "空响应"}`,
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      latencyMs: Date.now() - startedAt,
      model: requestModel,
      message: formatFetchError(error),
    };
  } finally {
    clearTimeout(timer);
  }
}

function getProviderTestModels(provider) {
  const support = normalizeModelSupport(provider.modelSupport);
  const remembered = support.preferredTestModel && !support.unsupportedModels.includes(support.preferredTestModel)
    ? [support.preferredTestModel]
    : [];
  return uniqueStrings([
    ...remembered,
    ...PROVIDER_TEST_MODELS.filter((model) => !support.unsupportedModels.includes(model)),
    ...PROVIDER_TEST_MODELS,
  ]);
}

function rememberProviderModelTest(provider, model, result) {
  const support = normalizeModelSupport(provider.modelSupport);
  if (result.ok) {
    support.supportedModels = uniqueStrings([model, ...support.supportedModels]);
    support.unsupportedModels = support.unsupportedModels.filter((item) => item !== model);
    support.preferredTestModel = model;
  } else if (isUnsupportedModelResult(result)) {
    support.unsupportedModels = uniqueStrings([...support.unsupportedModels, model]);
    support.supportedModels = support.supportedModels.filter((item) => item !== model);
    if (support.preferredTestModel === model) {
      support.preferredTestModel = support.supportedModels[0] || "";
    }
  }
  support.lastTestedAt = new Date().toISOString();
  provider.modelSupport = support;
}

function isUnsupportedModelResult(result) {
  const text = String(result?.message || "").toLowerCase();
  return result?.status === 404 ||
    result?.status === 400 ||
    result?.status === 422 ||
    text.includes("model_not_found") ||
    text.includes("model not found") ||
    text.includes("no available channel for model") ||
    text.includes("does not support") ||
    text.includes("unsupported model") ||
    text.includes("unknown model");
}

function shouldTryNextProviderTestModel(result, attemptCount, totalAttempts) {
  if (attemptCount >= totalAttempts) return false;
  if (isUnsupportedModelResult(result)) return true;
  const text = String(result?.message || "").toLowerCase();
  return result?.status === 200 &&
    (text.includes("不符合预期") || text.includes("空响应"));
}

function extractProviderTestAnswer(responseBody) {
  let payload;
  try {
    payload = JSON.parse(Buffer.from(responseBody).toString("utf8"));
  } catch {
    return "";
  }
  return extractTextFromPayload(payload).trim();
}

function extractTextFromPayload(payload) {
  if (!payload || typeof payload !== "object") return "";
  if (typeof payload.output_text === "string") return payload.output_text;
  if (typeof payload.text === "string") return payload.text;
  if (typeof payload.content === "string") return payload.content;
  if (Array.isArray(payload.output)) {
    return payload.output.map(extractTextFromPayload).filter(Boolean).join("");
  }
  if (Array.isArray(payload.content)) {
    return payload.content.map(extractTextFromPayload).filter(Boolean).join("");
  }
  if (payload.message) return extractTextFromPayload(payload.message);
  if (payload.delta) return extractTextFromPayload(payload.delta);
  if (Array.isArray(payload.choices)) {
    return payload.choices.map(extractTextFromPayload).filter(Boolean).join("");
  }
  if (payload.message?.content) return extractTextFromPayload(payload.message.content);
  if (payload.choices?.[0]?.message?.content) {
    return extractTextFromPayload(payload.choices[0].message.content);
  }
  return "";
}

function isProviderTestAnswerOk(answer) {
  const normalized = String(answer || "").toUpperCase().replace(/\s+/g, "");
  return normalized.includes(PROVIDER_TEST_EXPECTED_TEXT);
}

function safeTextFromBuffer(buffer) {
  try {
    return Buffer.from(buffer || []).toString("utf8").slice(0, 4000);
  } catch {
    return "";
  }
}

function truncateText(value, maxLength) {
  const text = String(value || "");
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

function buildUpstreamHeaders(clientReq, provider) {
  const headers = new Headers();
  for (const [key, value] of Object.entries(clientReq.headers)) {
    const lower = key.toLowerCase();
    if (HOP_BY_HOP_HEADERS.has(lower)) continue;
    if (lower === "authorization") continue;
    if (Array.isArray(value)) {
      for (const item of value) headers.append(key, item);
    } else if (value !== undefined) {
      headers.set(key, value);
    }
  }

  for (const [key, value] of Object.entries(provider.customHeaders || {})) {
    if (value !== undefined && value !== null && String(value) !== "") {
      headers.set(key, String(value));
    }
  }

  if (provider.apiKey) {
    headers.set("authorization", `Bearer ${provider.apiKey}`);
  }
  return headers;
}

function buildProviderOnlyHeaders(provider) {
  const headers = new Headers();
  if (provider.apiKey) {
    headers.set("authorization", `Bearer ${provider.apiKey}`);
  }
  for (const [key, value] of Object.entries(provider.customHeaders || {})) {
    if (value !== undefined && value !== null && String(value) !== "") {
      headers.set(key, String(value));
    }
  }
  return headers;
}

function rectifyRequestBody(provider, body) {
  if (!body?.length) return body;
  let json;
  try {
    json = JSON.parse(body.toString("utf8"));
  } catch {
    return body;
  }

  if (json && typeof json === "object" && !Array.isArray(json)) {
    if (json.model && provider.modelMap?.[json.model]) {
      json.model = provider.modelMap[json.model];
    }
    for (const key of provider.stripParams || []) {
      delete json[key];
    }
  }

  return Buffer.from(JSON.stringify(json));
}

function normalizeProxyPath(pathname) {
  let next = pathname;
  if (next.startsWith("/codex/")) {
    next = next.slice("/codex".length);
  }
  while (next.startsWith("/v1/v1/")) {
    next = next.slice(3);
  }
  if (next === "/models") return "/v1/models";
  if (next === "/responses" || next.startsWith("/responses/")) return `/v1${next}`;
  if (next === "/chat/completions") return "/v1/chat/completions";
  return next;
}

function joinUpstreamUrl(baseUrl, pathname, search) {
  const base = normalizeBaseUrl(baseUrl);
  if (!base) {
    throw nonRetryableError("供应商 Base URL 为空", 400);
  }
  let nextPath = pathname.startsWith("/") ? pathname : `/${pathname}`;
  if (base.endsWith("/v1") && nextPath.startsWith("/v1/")) {
    nextPath = nextPath.slice(3);
  }
  return `${base}${nextPath}${search || ""}`;
}

function isProxyRoute(pathname) {
  if (pathname === "/models" || pathname === "/responses") return true;
  if (pathname === "/chat/completions") return true;
  if (pathname.startsWith("/responses/")) return true;
  if (pathname.startsWith("/v1/")) return true;
  if (pathname.startsWith("/codex/v1/")) return true;
  return false;
}

function isStreamingRequest(req, pathname, body) {
  const accept = String(req.headers.accept || "").toLowerCase();
  if (accept.includes("text/event-stream")) return true;
  if (pathname.includes("stream")) return true;
  if (!body?.length) return false;
  try {
    const json = JSON.parse(body.toString("utf8"));
    return Boolean(json?.stream);
  } catch {
    return false;
  }
}

async function safeReadErrorBody(response) {
  try {
    const text = await response.text();
    return text.slice(0, 4000);
  } catch {
    return `HTTP ${response.status}`;
  }
}

function detectUpstreamPayloadError(text) {
  const raw = String(text || "").slice(0, 12000);
  if (!raw.trim()) return null;

  for (const payload of collectJsonPayloads(raw)) {
    const detected = detectErrorFromPayload(payload);
    if (detected) return detected;
  }
  const plain = detectErrorFromText(raw);
  if (plain) return plain;
  return null;
}

function detectErrorFromText(text) {
  const lower = text.toLowerCase();
  if (
    lower.includes("exceeded retry limit") &&
    (lower.includes("429") || lower.includes("too many requests"))
  ) {
    return {
      status: 429,
      retryable: true,
      message: extractErrorMessage(text) || "exceeded retry limit, last status: 429 Too Many Requests",
    };
  }
  if (
    lower.includes("too many requests") &&
    (lower.includes("\"error\"") || lower.includes("data:") || lower.includes("status"))
  ) {
    return {
      status: 429,
      retryable: true,
      message: extractErrorMessage(text) || "429 Too Many Requests",
    };
  }
  return null;
}

function collectJsonPayloads(text) {
  const payloads = [];
  pushJsonTextCandidate(payloads, text.trim());
  for (const line of text.split("\n")) {
    const item = line.trim();
    if (!item.startsWith("data:")) continue;
    const data = item.slice(5).trim();
    if (!data || data === "[DONE]") continue;
    pushJsonTextCandidate(payloads, data);
  }
  return payloads;
}

function detectErrorFromPayload(payload) {
  if (!payload || typeof payload !== "object") return null;
  const direct = payload.error || payload.response?.error || payload.failure || null;
  if (direct) {
    const status = Number(direct.status || direct.statusCode || direct.code);
    const message = String(direct.message || direct.error || direct.code || "");
    const code = String(direct.code || direct.type || payload.type || "").toLowerCase();
    if (status === 429 || code.includes("rate_limit") || code.includes("too_many_requests")) {
      return {
        status: 429,
        retryable: true,
        message: message || "429 Too Many Requests",
      };
    }
    if (status >= 500) {
      return { status, retryable: true, message: message || `HTTP ${status}` };
    }
  }

  const status = Number(payload.statusCode || payload.status);
  if (status === 429) {
    return {
      status: 429,
      retryable: true,
      message: String(payload.message || "429 Too Many Requests"),
    };
  }
  if (payload.response && typeof payload.response === "object") {
    return detectErrorFromPayload(payload.response);
  }
  return null;
}

function extractErrorMessage(text) {
  const match = String(text || "").match(/(?:message|error)["']?\s*[:=]\s*["']([^"']{1,500})/i);
  return match?.[1] || "";
}

async function readFirstChunk(reader, timeoutMs, controller) {
  try {
    const first = await readWithTimeout(reader, timeoutMs, controller);
    if (first.done) {
      throw retryableError("流式响应在首包到达前结束");
    }
    return first.value;
  } catch (error) {
    if (error.retryable) throw error;
    throw retryableError(`流式响应首包失败: ${error.message}`);
  }
}

async function readNextChunk(reader, timeoutMs, controller) {
  if (!timeoutMs) {
    return reader.read();
  }
  return readWithTimeout(reader, timeoutMs, controller);
}

async function readWithTimeout(reader, timeoutMs, controller) {
  let timer;
  try {
    return await Promise.race([
      reader.read(),
      new Promise((_, reject) => {
        timer = setTimeout(() => {
          controller.abort();
          reject(retryableError(`流式响应超时: ${timeoutMs}ms 无数据`));
        }, timeoutMs);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

function copyResponseHeaders(res, headers, mode) {
  headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (HOP_BY_HOP_HEADERS.has(lower)) return;
    if (lower === "content-length") return;
    if (lower === "content-encoding") return;
    res.setHeader(key, value);
  });
  if (mode === "stream") {
    res.setHeader("cache-control", "no-cache");
    res.setHeader("x-accel-buffering", "no");
  }
}

async function serveStatic(req, res, url) {
  let filePath = url.pathname === "/" ? "/index.html" : url.pathname;
  filePath = path.normalize(filePath).replace(/^(\.\.[/\\])+/, "");
  const absPath = path.join(PUBLIC_DIR, filePath);
  if (!absPath.startsWith(PUBLIC_DIR)) {
    sendText(res, 403, "禁止访问");
    return;
  }

  try {
    const info = await stat(absPath);
    if (!info.isFile()) {
      sendText(res, 404, "页面不存在");
      return;
    }
    res.statusCode = 200;
    res.setHeader("content-type", contentType(absPath));
    createReadStream(absPath).pipe(res);
  } catch {
    sendText(res, 404, "页面不存在");
  }
}

async function readJsonBody(req) {
  const body = await readRawBody(req);
  if (!body.length) return {};
  try {
    return JSON.parse(body.toString("utf8"));
  } catch {
    throw nonRetryableError("请求体不是合法 JSON", 400);
  }
}

async function readRawBody(req) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > MAX_BODY_BYTES) {
      throw nonRetryableError("请求体过大", 413);
    }
    chunks.push(chunk);
  }
  return Buffer.concat(chunks);
}

function sendJson(res, statusCode, payload) {
  res.statusCode = statusCode;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.end(`${JSON.stringify(payload)}\n`);
}

function sendText(res, statusCode, text) {
  res.statusCode = statusCode;
  res.setHeader("content-type", "text/plain; charset=utf-8");
  res.end(text);
}

function assertAdminAccess(req, res) {
  return true;
}

function assertProxyAccess(req, res) {
  if (!PROXY_TOKEN) return true;
  if (req.headers["x-lite-ccswitch-token"] === PROXY_TOKEN) return true;
  sendJson(res, 401, {
    error: {
      message: "代理访问令牌无效",
      type: "proxy_auth_failed",
    },
  });
  return false;
}

function retryableError(message, status = 502) {
  const error = new Error(message);
  error.retryable = true;
  error.status = status;
  return error;
}

function nonRetryableError(message, status = 400) {
  const error = new Error(message);
  error.retryable = false;
  error.status = status;
  return error;
}

function upstreamError(status, body, retryable) {
  const summary = body ? `HTTP ${status}: ${body}` : `HTTP ${status}`;
  const error = new Error(summary);
  error.retryable = retryable;
  error.status = status;
  return error;
}

function isRetryableStatus(status) {
  return !NON_RETRYABLE_STATUS.has(status);
}

function findProvider(providerId) {
  if (!providerId) return null;
  return config.providers.find((provider) => provider.id === providerId) || null;
}

function sortProviders() {
  config.providers.sort(compareProviders);
}

function compareProviders(a, b) {
  return (a.sortIndex || 999_999) - (b.sortIndex || 999_999) ||
    a.name.localeCompare(b.name, "zh-CN") ||
    a.id.localeCompare(b.id);
}

function shouldSendBody(method = "GET") {
  return !["GET", "HEAD"].includes(method.toUpperCase());
}

function normalizeBaseUrl(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

function normalizeObject(value) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? { ...value }
    : {};
}

function normalizeModelSupport(value) {
  const input = value && typeof value === "object" && !Array.isArray(value)
    ? value
    : {};
  return {
    preferredTestModel: String(input.preferredTestModel || input.preferred_test_model || ""),
    supportedModels: uniqueStrings(input.supportedModels || input.supported_models || []),
    unsupportedModels: uniqueStrings(input.unsupportedModels || input.unsupported_models || []),
    lastTestedAt: String(input.lastTestedAt || input.last_tested_at || ""),
  };
}

function uniqueStrings(values) {
  const result = [];
  const seen = new Set();
  for (const value of Array.isArray(values) ? values : []) {
    const text = String(value || "").trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    result.push(text);
  }
  return result;
}

function positiveInt(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback;
}

function clampNumber(value, fallback, min, max) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

function nonNegativeNumber(value, fallback) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) return fallback;
  return parsed;
}

function roundNumber(value, digits = 0) {
  const factor = 10 ** digits;
  return Math.round(Number(value || 0) * factor) / factor;
}

function bytesToMb(value) {
  return roundNumber(Number(value || 0) / 1024 / 1024, 1);
}

function roundMoney(value) {
  return Math.round(Number(value || 0) * 1_000_000) / 1_000_000;
}

function maskSecret(value) {
  const text = String(value || "");
  if (!text) return "";
  if (text.length <= 8) return "********";
  return `${text.slice(0, 4)}...${text.slice(-4)}`;
}

function maskHeaders(headers) {
  const result = {};
  for (const [key, value] of Object.entries(headers || {})) {
    result[key] = /key|token|authorization|secret/i.test(key)
      ? maskSecret(value)
      : value;
  }
  return result;
}

function contentType(filePath) {
  if (filePath.endsWith(".html")) return "text/html; charset=utf-8";
  if (filePath.endsWith(".css")) return "text/css; charset=utf-8";
  if (filePath.endsWith(".js")) return "application/javascript; charset=utf-8";
  if (filePath.endsWith(".svg")) return "image/svg+xml";
  return "application/octet-stream";
}

function parseUrl(req) {
  return new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
}

function formatFetchError(error) {
  if (error?.name === "AbortError") return "请求超时或被中断";
  return error instanceof Error ? error.message : String(error);
}

function onceDrain(stream) {
  return new Promise((resolve, reject) => {
    stream.once("drain", resolve);
    stream.once("error", reject);
  });
}
