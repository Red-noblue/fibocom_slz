/**
 * 服务器版 UsageDashboard。
 * 迁移 ccswitch 用量页的 Hero、统计表和请求日志外观，数据改为读取 /api/billing/*。
 */
import { Activity, ArrowDownToLine, ArrowUpFromLine, ChevronLeft, ChevronRight, Coins, Database, RefreshCw, TrendingUp, Zap } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { formatCompactNumber, formatMoney, formatNumber, formatTime } from "./format.js";

export function UsageDashboard({
  billing,
  logs,
  providers = [],
  providerFilter,
  onProviderFilterChange,
  pricing,
  setPricing,
  onSavePricing,
  onRefresh,
}) {
  const [statusFilter, setStatusFilter] = useState("all");
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");
  const rangedLogs = useMemo(
    () => filterUsageLogs(logs, { providerFilter, startAt, endAt }),
    [logs, providerFilter, startAt, endAt],
  );
  const filteredBilling = useMemo(
    () => buildUsageSummaryFromLogs(rangedLogs, billing?.pricing),
    [rangedLogs, billing?.pricing],
  );
  const usageProviders = filteredBilling.providers || [];
  const models = filteredBilling.models || [];
  const dayRows = filteredBilling.days || [];
  const filteredLogs = useMemo(() => {
    if (statusFilter === "all") return rangedLogs;
    return rangedLogs.filter((log) => String(log.statusCode) === statusFilter);
  }, [rangedLogs, statusFilter]);

  return (
    <section className="usage-dashboard">
      <div className="usage-toolbar">
        <div>
          <h2>{providerFilter ? `${providerFilter.name} 使用统计` : "使用统计"}</h2>
          <p>按供应商和时间范围统计请求、Token 与估算成本。</p>
        </div>
        <div className="usage-toolbar-actions">
          {providerFilter && (
            <button className="cc-button cc-button-secondary" onClick={() => onProviderFilterChange?.(null)}>
              全部供应商
            </button>
          )}
          <button className="cc-button cc-button-secondary" onClick={onRefresh}>
            <RefreshCw size={15} />
            刷新
          </button>
        </div>
      </div>

      <UsageFilters
        providers={providers}
        providerFilter={providerFilter}
        onProviderFilterChange={onProviderFilterChange}
        startAt={startAt}
        endAt={endAt}
        setStartAt={setStartAt}
        setEndAt={setEndAt}
      />

      <UsageHero billing={filteredBilling} providerFilter={providerFilter} />

      <UsageTrendChart logs={rangedLogs} />

      <div className="usage-grid">
        <DailyUsageTable rows={dayRows} />
        <UsageStatsTable title="供应商统计" firstColumn="Provider" rows={usageProviders} />
      </div>

      <div className="usage-grid">
        <UsageStatsTable title="模型统计" firstColumn="Model" rows={models} />
        <PricingPanel pricing={pricing} setPricing={setPricing} onSavePricing={onSavePricing} />
      </div>

      <div className="usage-grid">
        <RequestLogTable logs={filteredLogs} statusFilter={statusFilter} setStatusFilter={setStatusFilter} />
      </div>
    </section>
  );
}

function UsageFilters({
  providers,
  providerFilter,
  onProviderFilterChange,
  startAt,
  endAt,
  setStartAt,
  setEndAt,
}) {
  return (
    <article className="usage-card usage-filter-card">
      <div className="usage-filter-grid">
        <label>
          <span>供应商</span>
          <select
            value={providerFilter?.id || "all"}
            onChange={(event) => {
              const next = providers.find((provider) => provider.id === event.target.value);
              onProviderFilterChange?.(next ? { id: next.id, name: next.name } : null);
            }}
          >
            <option value="all">全部供应商</option>
            {providers.map((provider) => (
              <option value={provider.id} key={provider.id}>{provider.name}</option>
            ))}
          </select>
        </label>
        <label>
          <span>开始时间</span>
          <input type="datetime-local" value={startAt} onChange={(event) => setStartAt(event.target.value)} />
        </label>
        <label>
          <span>结束时间</span>
          <input type="datetime-local" value={endAt} onChange={(event) => setEndAt(event.target.value)} />
        </label>
        <div className="usage-filter-actions">
          <button className="cc-button cc-button-secondary" type="button" onClick={() => applyToday(setStartAt, setEndAt)}>今天</button>
          <button className="cc-button cc-button-secondary" type="button" onClick={() => applyLastDays(setStartAt, setEndAt, 7)}>近 7 天</button>
          <button className="cc-button cc-button-secondary" type="button" onClick={() => { setStartAt(""); setEndAt(""); }}>全部时间</button>
        </div>
      </div>
    </article>
  );
}

function UsageTrendChart({ logs }) {
  const chart = useMemo(() => buildTrendChart(logs), [logs]);
  const [hoveredKey, setHoveredKey] = useState(null);
  const hoveredPoint = chart.points.find((point) => point.key === hoveredKey) || null;

  return (
    <article className="usage-card usage-trend-card">
      <div className="usage-card-head">
        <div>
          <h3>使用趋势</h3>
          <p>按时间聚合最近请求，展示输入、输出、缓存命中与成本变化。</p>
        </div>
        <span className="state-pill ok">
          <TrendingUp size={13} />
          最近 {formatNumber(logs.length)} 条
        </span>
      </div>
      <div className="usage-trend-legend">
        <TrendLegend color="#3b82f6" label="输入 Tokens" />
        <TrendLegend color="#22c55e" label="输出 Tokens" />
        <TrendLegend color="#f97316" label="缓存写入" />
        <TrendLegend color="#8b5cf6" label="缓存命中" />
        <TrendLegend color="#f43f5e" label="成本" dashed />
      </div>
      {chart.points.length ? (
        <div className="usage-trend-chart-wrap" onMouseLeave={() => setHoveredKey(null)}>
          <svg className="usage-trend-svg" viewBox="0 0 760 300" role="img" aria-label="使用趋势">
            <defs>
              <linearGradient id="trendInput" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity="0.22" />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity="0" />
              </linearGradient>
              <linearGradient id="trendOutput" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity="0.2" />
                <stop offset="95%" stopColor="#22c55e" stopOpacity="0" />
              </linearGradient>
              <linearGradient id="trendCacheWrite" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f97316" stopOpacity="0.18" />
                <stop offset="95%" stopColor="#f97316" stopOpacity="0" />
              </linearGradient>
              <linearGradient id="trendCacheRead" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity="0.18" />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity="0" />
              </linearGradient>
            </defs>
            <g className="trend-grid">
              {[0, 1, 2, 3].map((item) => (
                <line key={item} x1="56" x2="704" y1={44 + item * 58} y2={44 + item * 58} />
              ))}
            </g>
            <text className="trend-axis-label" x="18" y="48">{formatCompactNumber(chart.tokenMax)}</text>
            <text className="trend-axis-label" x="24" y="224">0</text>
            <text className="trend-axis-label right" x="724" y="48">{formatMoney(chart.costMax, 2)}</text>
            <text className="trend-axis-label right" x="724" y="224">$0</text>
            <TrendArea areaPath={chart.paths.inputArea} linePath={chart.paths.inputLine} color="#3b82f6" fill="url(#trendInput)" />
            <TrendArea areaPath={chart.paths.outputArea} linePath={chart.paths.outputLine} color="#22c55e" fill="url(#trendOutput)" />
            <TrendArea areaPath={chart.paths.cacheCreationArea} linePath={chart.paths.cacheCreationLine} color="#f97316" fill="url(#trendCacheWrite)" />
            <TrendArea areaPath={chart.paths.cacheReadArea} linePath={chart.paths.cacheReadLine} color="#8b5cf6" fill="url(#trendCacheRead)" />
            <path className="trend-line cost" d={chart.paths.costLine} />
            {hoveredPoint && <TrendHoverMarks point={hoveredPoint} />}
            {chart.points.map((point) => (
              <g key={point.key}>
                <circle className="trend-point" cx={point.x} cy={point.inputY} r="3" />
                <text className="trend-x-label" x={point.x} y="270">{point.shortLabel}</text>
                <rect
                  className="trend-hover-zone"
                  x={point.x - chart.hoverBandWidth / 2}
                  y="26"
                  width={chart.hoverBandWidth}
                  height="226"
                  onMouseEnter={() => setHoveredKey(point.key)}
                  onMouseMove={() => setHoveredKey(point.key)}
                />
              </g>
            ))}
          </svg>
          {hoveredPoint && <TrendTooltip point={hoveredPoint} />}
        </div>
      ) : (
        <div className="trend-empty">暂无请求趋势数据</div>
      )}
    </article>
  );
}

function TrendLegend({ color, label, dashed = false }) {
  return (
    <span>
      <i style={{ backgroundColor: dashed ? "transparent" : color, borderColor: color, borderStyle: dashed ? "dashed" : "solid" }} />
      {label}
    </span>
  );
}

function TrendArea({ areaPath, linePath, color, fill }) {
  return (
    <>
      <path className="trend-area" d={areaPath} fill={fill} />
      <path className="trend-line" d={linePath} style={{ stroke: color }} />
    </>
  );
}

function TrendHoverMarks({ point }) {
  return (
    <g className="trend-hover-marks">
      <line className="trend-crosshair" x1={point.x} x2={point.x} y1="34" y2="232" />
      <circle className="trend-focus-point input" cx={point.x} cy={point.inputY} r="4" />
      <circle className="trend-focus-point output" cx={point.x} cy={point.outputY} r="4" />
      <circle className="trend-focus-point cache-write" cx={point.x} cy={point.cacheCreationY} r="4" />
      <circle className="trend-focus-point cache-read" cx={point.x} cy={point.cacheReadY} r="4" />
      <circle className="trend-focus-point cost" cx={point.x} cy={point.costY} r="4" />
    </g>
  );
}

function TrendTooltip({ point }) {
  const left = Math.max(12, Math.min(70, (point.x / 760) * 100));
  return (
    <div className="usage-trend-tooltip" style={{ left: `${left}%` }}>
      <strong>{point.label}</strong>
      <span>输入：{formatNumber(point.inputTokens)}</span>
      <span>输出：{formatNumber(point.outputTokens)}</span>
      <span>缓存写入：{formatNumber(point.cacheCreationTokens)}</span>
      <span>缓存命中：{formatNumber(point.cacheReadTokens)}</span>
      <span>成本：{formatMoney(point.cost, 4)}</span>
    </div>
  );
}

function buildTrendChart(logs) {
  const values = bucketTrendLogs(logs);
  const top = 34;
  const bottom = 232;
  const left = 56;
  const right = 704;
  const chartWidth = right - left;
  const chartHeight = bottom - top;
  const tokenMax = Math.max(
    1,
    ...values.flatMap((item) => [
      item.inputTokens,
      item.outputTokens,
      item.cacheCreationTokens,
      item.cacheReadTokens,
    ]),
  );
  const costMax = Math.max(0.000001, ...values.map((item) => item.cost));
  const points = values.map((item, index) => {
    const x = values.length === 1
      ? left + chartWidth / 2
      : left + (chartWidth * index) / (values.length - 1);
    const tokenY = (value) => bottom - (Number(value || 0) / tokenMax) * chartHeight;
    const costY = bottom - (Number(item.cost || 0) / costMax) * chartHeight;
    return {
      ...item,
      x,
      inputY: tokenY(item.inputTokens),
      outputY: tokenY(item.outputTokens),
      cacheCreationY: tokenY(item.cacheCreationTokens),
      cacheReadY: tokenY(item.cacheReadTokens),
      costY,
      tooltip: `${item.label}\n输入 ${formatNumber(item.inputTokens)}\n输出 ${formatNumber(item.outputTokens)}\n缓存读 ${formatNumber(item.cacheReadTokens)}\n缓存写 ${formatNumber(item.cacheCreationTokens)}\n成本 ${formatMoney(item.cost, 4)}`,
    };
  });
  return {
    points,
    tokenMax,
    costMax,
    hoverBandWidth: Math.max(18, Math.min(72, chartWidth / Math.max(1, points.length))),
    paths: {
      inputLine: buildLinePath(points, "inputY"),
      outputLine: buildLinePath(points, "outputY"),
      cacheCreationLine: buildLinePath(points, "cacheCreationY"),
      cacheReadLine: buildLinePath(points, "cacheReadY"),
      costLine: buildLinePath(points, "costY"),
      inputArea: buildAreaPath(points, "inputY", bottom),
      outputArea: buildAreaPath(points, "outputY", bottom),
      cacheCreationArea: buildAreaPath(points, "cacheCreationY", bottom),
      cacheReadArea: buildAreaPath(points, "cacheReadY", bottom),
    },
  };
}

function bucketTrendLogs(logs) {
  const items = logs
    .map((log) => ({ ...log, time: Date.parse(log.timestamp || "") }))
    .filter((log) => Number.isFinite(log.time))
    .sort((a, b) => a.time - b.time);
  if (!items.length) return [];
  const first = items[0].time;
  const last = items[items.length - 1].time;
  const span = Math.max(1, last - first);
  const bucketMs = span <= 2 * 60 * 60 * 1000
    ? 5 * 60 * 1000
    : span <= 48 * 60 * 60 * 1000
      ? 60 * 60 * 1000
      : 24 * 60 * 60 * 1000;
  const buckets = new Map();
  for (const log of items) {
    const bucketTime = Math.floor(log.time / bucketMs) * bucketMs;
    const bucket = buckets.get(bucketTime) || {
      key: String(bucketTime),
      time: bucketTime,
      inputTokens: 0,
      outputTokens: 0,
      cacheReadTokens: 0,
      cacheCreationTokens: 0,
      cost: 0,
    };
    bucket.inputTokens += Number(log.inputTokens || 0);
    bucket.outputTokens += Number(log.outputTokens || 0);
    bucket.cacheReadTokens += Number(log.cacheReadTokens || 0);
    bucket.cacheCreationTokens += Number(log.cacheCreationTokens || 0);
    bucket.cost += Number(log.estimatedCostUsd || 0);
    buckets.set(bucketTime, bucket);
  }
  return Array.from(buckets.values()).map((bucket, index, list) => {
    const date = new Date(bucket.time);
    const label = bucketMs >= 24 * 60 * 60 * 1000
      ? date.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" })
      : date.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false });
    return {
      ...bucket,
      label,
      shortLabel: compactTrendLabel(label, index, list.length),
    };
  });
}

function compactTrendLabel(label, index, total) {
  if (total > 10 && index % Math.ceil(total / 8) !== 0 && index !== total - 1) return "";
  return label.replace(/^\d{2}\//, "");
}

function buildLinePath(points, yKey) {
  if (!points.length) return "";
  return points.map((point, index) => `${index === 0 ? "M" : "L"} ${roundSvg(point.x)} ${roundSvg(point[yKey])}`).join(" ");
}

function buildAreaPath(points, yKey, baseline) {
  if (!points.length) return "";
  const line = buildLinePath(points, yKey);
  const first = points[0];
  const last = points[points.length - 1];
  return `${line} L ${roundSvg(last.x)} ${baseline} L ${roundSvg(first.x)} ${baseline} Z`;
}

function roundSvg(value) {
  return Math.round(Number(value || 0) * 10) / 10;
}

function UsageHero({ billing, providerFilter }) {
  return (
    <article className="usage-hero">
      <div className="usage-hero-top">
        <div className="usage-hero-title">
          <div className="usage-hero-icon">
            <Zap size={21} />
          </div>
          <div>
            <span>{providerFilter ? `${providerFilter.name} · Codex` : "全部应用 · Codex"}</span>
            <strong>{formatCompactNumber(billing?.totalTokens)} Tokens</strong>
          </div>
        </div>
        <div className="usage-hero-side">
          <span>{formatNumber(billing?.totalRequests)} 请求</span>
          <strong>{formatMoney(billing?.estimatedCostUsd)}</strong>
        </div>
      </div>

      <div className="usage-token-row">
        <TokenMetric icon={<ArrowDownToLine size={15} />} label="输入" value={billing?.inputTokens} />
        <TokenMetric icon={<ArrowUpFromLine size={15} />} label="输出" value={billing?.outputTokens} />
        <TokenMetric icon={<Database size={15} />} label="缓存读取" value={billing?.cacheReadTokens} />
        <TokenMetric icon={<Activity size={15} />} label="成功请求" value={billing?.successRequests} />
      </div>
    </article>
  );
}

function DailyUsageTable({ rows }) {
  return (
    <article className="usage-card">
      <h3>每日统计</h3>
      <div className="cc-table">
        <table>
          <thead>
            <tr>
              <th>日期</th>
              <th className="right">请求数</th>
              <th className="right">输入</th>
              <th className="right">输出</th>
              <th className="right">Tokens</th>
              <th className="right">成本</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? rows.map((row) => (
              <tr key={row.name}>
                <td className="strong">{row.name}</td>
                <td className="right">{formatNumber(row.requests)}</td>
                <td className="right">{formatNumber(row.inputTokens)}</td>
                <td className="right">{formatNumber(row.outputTokens)}</td>
                <td className="right">{formatNumber(row.totalTokens)}</td>
                <td className="right">{formatMoney(row.estimatedCostUsd, 4)}</td>
              </tr>
            )) : <tr><td colSpan="6" className="empty-cell">暂无数据</td></tr>}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function TokenMetric({ icon, label, value }) {
  return (
    <div className="usage-token-metric">
      <span>{icon}{label}</span>
      <strong>{formatNumber(value)}</strong>
    </div>
  );
}

function UsageStatsTable({ title, firstColumn, rows }) {
  return (
    <article className="usage-card">
      <h3>{title}</h3>
      <div className="cc-table">
        <table>
          <thead>
            <tr>
              <th>{firstColumn}</th>
              <th className="right">请求数</th>
              <th className="right">Tokens</th>
              <th className="right">成本</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? rows.slice(0, 12).map((row) => (
              <tr key={row.name}>
                <td className="strong">{row.name}</td>
                <td className="right">{formatNumber(row.requests)}</td>
                <td className="right">{formatNumber(row.totalTokens)}</td>
                <td className="right">{formatMoney(row.estimatedCostUsd, 4)}</td>
              </tr>
            )) : <tr><td colSpan="4" className="empty-cell">暂无数据</td></tr>}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function PricingPanel({ pricing, setPricing, onSavePricing }) {
  return (
    <article className="usage-card">
      <div className="usage-card-head">
        <div>
          <h3>价格配置</h3>
          <p>单位为 USD / 百万 Token；gpt-5.4 / gpt-5.5 会统一按 gpt-5.5 价格估算，Fast 模式按 2.5x 计费。</p>
        </div>
        <button className="cc-button cc-button-primary" onClick={onSavePricing}>
          <Coins size={15} />
          保存
        </button>
      </div>
      <div className="cc-table">
        <table>
          <thead>
            <tr>
              <th>模型</th>
              <th>输入</th>
              <th>输出</th>
              <th>缓存读</th>
              <th>缓存写</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {pricing.map((row, index) => (
              <tr key={index}>
                <td><input value={row.model} onChange={(event) => updateRow(index, "model", event.target.value)} placeholder="gpt-5 或 *" /></td>
                <td><input type="number" min="0" step="0.000001" value={row.inputPerMillion} onChange={(event) => updateRow(index, "inputPerMillion", event.target.value)} /></td>
                <td><input type="number" min="0" step="0.000001" value={row.outputPerMillion} onChange={(event) => updateRow(index, "outputPerMillion", event.target.value)} /></td>
                <td><input type="number" min="0" step="0.000001" value={row.cacheReadPerMillion} onChange={(event) => updateRow(index, "cacheReadPerMillion", event.target.value)} /></td>
                <td><input type="number" min="0" step="0.000001" value={row.cacheCreationPerMillion} onChange={(event) => updateRow(index, "cacheCreationPerMillion", event.target.value)} /></td>
                <td><button className="cc-button cc-button-secondary" onClick={() => setPricing((items) => items.filter((_, i) => i !== index))}>删除</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button className="cc-button cc-button-secondary add-row" onClick={() => setPricing((items) => [...items, { model: "", inputPerMillion: 0, outputPerMillion: 0, cacheReadPerMillion: 0, cacheCreationPerMillion: 0 }])}>添加价格行</button>
    </article>
  );

  function updateRow(index, key, value) {
    setPricing((items) => items.map((item, i) => i === index ? { ...item, [key]: value } : item));
  }
}

function RequestLogTable({ logs, statusFilter, setStatusFilter }) {
  const pageSize = 30;
  const [page, setPage] = useState(0);
  const totalPages = Math.max(1, Math.ceil(logs.length / pageSize));
  const currentPage = Math.min(page, totalPages - 1);
  const pageLogs = logs.slice(currentPage * pageSize, currentPage * pageSize + pageSize);

  useEffect(() => {
    setPage(0);
  }, [statusFilter, logs.length]);

  return (
    <article className="usage-card">
      <div className="usage-card-head">
        <div>
          <h3>请求日志</h3>
          <p>每页显示 30 条请求，避免大量日志同时渲染。</p>
        </div>
        <span className="state-pill neutral">{formatNumber(logs.length)} 条</span>
      </div>
      <div className="usage-log-filters">
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="all">全部状态</option>
          <option value="200">200 OK</option>
          <option value="400">400</option>
          <option value="401">401</option>
          <option value="429">429</option>
          <option value="500">500</option>
          <option value="502">502</option>
          <option value="503">503</option>
        </select>
      </div>
      <div className="cc-table">
        <table>
          <thead>
            <tr>
              <th className="center">时间</th>
              <th className="center">供应商</th>
              <th className="center">模型</th>
              <th className="center">计费模型</th>
              <th className="center">模式</th>
              <th className="center">输入</th>
              <th className="center">输出</th>
              <th className="center">成本</th>
              <th className="center">状态</th>
            </tr>
          </thead>
          <tbody>
            {pageLogs.length ? pageLogs.map((log) => (
              <tr key={log.id}>
                <td className="center">{formatTime(log.timestamp)}</td>
                <td className="center">{log.providerName || "未知"}</td>
                <td className="center mono">{log.responseModel || log.requestModel || "unknown"}</td>
                <td className="center mono">{log.billingModel || log.responseModel || log.requestModel || "unknown"}</td>
                <td className="center">
                  <span className={`state-pill ${log.billingMode === "fast" ? "warn" : "neutral"}`}>
                    {log.billingMode === "fast" ? `Fast x${log.billingMultiplier || 2.5}` : "标准"}
                  </span>
                </td>
                <td className="center">{formatNumber(log.inputTokens)}</td>
                <td className="center">{formatNumber(log.outputTokens)}</td>
                <td className="center">{formatMoney(log.estimatedCostUsd, 4)}</td>
                <td className="center">
                  <span className={`state-pill ${log.error || log.statusCode >= 400 ? "bad" : "ok"}`}>{log.statusCode}</span>
                </td>
              </tr>
            )) : <tr><td colSpan="9" className="empty-cell">暂无数据</td></tr>}
          </tbody>
        </table>
      </div>
      <LogPagination
        page={currentPage}
        totalPages={totalPages}
        total={logs.length}
        pageSize={pageSize}
        onPageChange={setPage}
      />
    </article>
  );
}

function LogPagination({ page, totalPages, total, pageSize, onPageChange }) {
  const pages = buildPageItems(page, totalPages);
  return (
    <div className="log-pagination">
      <span>共 {formatNumber(total)} 条 · 每页 {pageSize} 条</span>
      <div className="log-pagination-actions">
        <button className="cc-button cc-button-secondary cc-button-sm" disabled={page === 0} onClick={() => onPageChange(Math.max(0, page - 1))}>
          <ChevronLeft size={14} />
        </button>
        {pages.map((item, index) => item === "ellipsis" ? (
          <span className="pagination-ellipsis" key={`${item}-${index}`}>...</span>
        ) : (
          <button
            className={`page-button ${item === page ? "active" : ""}`}
            key={item}
            onClick={() => onPageChange(item)}
          >
            {item + 1}
          </button>
        ))}
        <button className="cc-button cc-button-secondary cc-button-sm" disabled={page >= totalPages - 1} onClick={() => onPageChange(Math.min(totalPages - 1, page + 1))}>
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

function buildPageItems(page, totalPages) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index);
  }
  const selected = new Set([0, 1, totalPages - 2, totalPages - 1, page - 1, page, page + 1]);
  const sorted = Array.from(selected)
    .filter((item) => item >= 0 && item < totalPages)
    .sort((a, b) => a - b);
  const result = [];
  for (const item of sorted) {
    if (result.length && item - result[result.length - 1] > 1) {
      result.push("ellipsis");
    }
    result.push(item);
  }
  return result;
}

function filterUsageLogs(logs, { providerFilter, startAt, endAt }) {
  const startTime = parseLocalDateTime(startAt);
  const endTime = parseLocalDateTime(endAt);
  return (logs || []).filter((log) => {
    if (providerFilter?.id && log.providerId !== providerFilter.id) return false;
    const time = Date.parse(log.timestamp || "");
    if (!Number.isFinite(time)) return false;
    if (startTime !== null && time < startTime) return false;
    if (endTime !== null && time > endTime) return false;
    return true;
  });
}

function buildUsageSummaryFromLogs(logs, pricing) {
  const summary = {
    totalRequests: logs.length,
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
    days: {},
    pricing,
  };

  for (const log of logs) {
    const ok = Number(log.statusCode || 0) >= 200 && Number(log.statusCode || 0) < 400 && !log.error;
    if (ok) summary.successRequests += 1;
    else summary.failedRequests += 1;
    addUsageTotals(summary, log);

    const providerKey = log.providerName || log.providerId || "未选择";
    summary.providers[providerKey] ??= emptyUsageBucket(providerKey);
    summary.providers[providerKey].requests += 1;
    addUsageTotals(summary.providers[providerKey], log);

    const modelKey = log.billingModel || log.responseModel || log.requestModel || "unknown";
    summary.models[modelKey] ??= emptyUsageBucket(modelKey);
    summary.models[modelKey].requests += 1;
    addUsageTotals(summary.models[modelKey], log);

    const dayKey = formatDayKey(log.timestamp);
    summary.days[dayKey] ??= emptyUsageBucket(dayKey);
    summary.days[dayKey].requests += 1;
    addUsageTotals(summary.days[dayKey], log);
  }

  return {
    ...summary,
    providers: Object.values(summary.providers).sort(compareUsageBuckets),
    models: Object.values(summary.models).sort(compareUsageBuckets),
    days: Object.values(summary.days).sort((a, b) => String(b.name).localeCompare(String(a.name))),
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

function addUsageTotals(target, log) {
  target.inputTokens += Number(log.inputTokens || 0);
  target.outputTokens += Number(log.outputTokens || 0);
  target.cacheReadTokens += Number(log.cacheReadTokens || 0);
  target.cacheCreationTokens += Number(log.cacheCreationTokens || 0);
  target.totalTokens += Number(log.totalTokens || 0);
  target.estimatedCostUsd += Number(log.estimatedCostUsd || 0);
}

function compareUsageBuckets(a, b) {
  return (b.estimatedCostUsd - a.estimatedCostUsd) ||
    (b.totalTokens - a.totalTokens) ||
    String(a.name).localeCompare(String(b.name), "zh-CN");
}

function parseLocalDateTime(value) {
  if (!value) return null;
  const time = Date.parse(value);
  return Number.isFinite(time) ? time : null;
}

function formatDayKey(timestamp) {
  const time = Date.parse(timestamp || "");
  if (!Number.isFinite(time)) return "未知日期";
  return new Date(time).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function applyToday(setStartAt, setEndAt) {
  const now = new Date();
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  setStartAt(toDatetimeLocalValue(start));
  setEndAt(toDatetimeLocalValue(now));
}

function applyLastDays(setStartAt, setEndAt, days) {
  const now = new Date();
  const start = new Date(now.getTime() - Math.max(1, Number(days || 1)) * 24 * 60 * 60 * 1000);
  setStartAt(toDatetimeLocalValue(start));
  setEndAt(toDatetimeLocalValue(now));
}

function toDatetimeLocalValue(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return [
    date.getFullYear(),
    "-",
    pad(date.getMonth() + 1),
    "-",
    pad(date.getDate()),
    "T",
    pad(date.getHours()),
    ":",
    pad(date.getMinutes()),
  ].join("");
}
