/**
 * Lite CC Switch React 管理台主入口。
 * 采用 ccswitch 的 React/Vite 前端体系，改为通过服务器 HTTP API 管理本机代理。
 */
import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BarChart3,
  CheckCircle2,
  Cpu,
  GitBranch,
  Loader2,
  MemoryStick,
  Plus,
  RefreshCw,
  Search,
  Server,
  Settings,
  Shield,
  X,
} from "lucide-react";
import { ProviderCard } from "./components/ProviderCard.jsx";
import { UsageDashboard } from "./components/UsageDashboard.jsx";
import { formatNumber } from "./components/format.js";
import "./styles.css";

const initialProviderForm = {
  name: "",
  baseUrl: "",
  apiKey: "",
  sortIndex: 1,
  notes: "",
};

function App() {
  const [activeView, setActiveView] = useState("providers");
  const [status, setStatus] = useState(null);
  const [billing, setBilling] = useState(null);
  const [logs, setLogs] = useState([]);
  const [pricing, setPricing] = useState([{ model: "*", inputPerMillion: 0, outputPerMillion: 0, cacheReadPerMillion: 0, cacheCreationPerMillion: 0 }]);
  const [proxyDraft, setProxyDraft] = useState(null);
  const [providerForm, setProviderForm] = useState(initialProviderForm);
  const [providerSearch, setProviderSearch] = useState("");
  const [providerTestResults, setProviderTestResults] = useState({});
  const [usageProviderFilter, setUsageProviderFilter] = useState(null);
  const [events, setEvents] = useState(["等待状态..."]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function refresh(silent = false) {
    try {
      if (!silent) setLoading(true);
      const todayStart = new Date();
      todayStart.setHours(0, 0, 0, 0);
      const [nextStatus, nextBilling, nextLogs] = await Promise.all([
        api("/api/status"),
        api(`/api/billing/summary?startAt=${encodeURIComponent(todayStart.toISOString())}`),
        api("/api/billing/logs?limit=5000"),
      ]);
      setStatus(nextStatus);
      setBilling(nextBilling);
      setLogs(nextLogs.records || []);
      setProxyDraft((current) => current || cloneProxy(nextStatus.proxy));
      setPricing((current) => current.length && current.some((row) => row.model) ? current : pricingToRows(nextBilling.pricing?.pricing || {}));
      if (!silent) pushEvent("状态已刷新");
    } catch (error) {
      pushEvent(`刷新失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    const timer = setInterval(() => refresh(true), 5000);
    return () => clearInterval(timer);
  }, []);

  const providers = useMemo(
    () => (status?.providers || []).slice().sort((a, b) => (a.sortIndex || 999999) - (b.sortIndex || 999999)),
    [status],
  );
  const filteredProviders = useMemo(() => {
    const keyword = providerSearch.trim().toLowerCase();
    if (!keyword) return providers;
    return providers.filter((provider) => {
      const haystack = [
        provider.name,
        provider.baseUrl,
        provider.notes,
        provider.apiKeyMasked,
      ].join(" ").toLowerCase();
      return haystack.includes(keyword);
    });
  }, [providers, providerSearch]);
  const providerBillingByName = useMemo(() => {
    const map = new Map();
    for (const item of billing?.providers || []) {
      map.set(item.name, item);
    }
    return map;
  }, [billing]);

  function pushEvent(message) {
    const line = `[${new Date().toLocaleTimeString("zh-CN", { hour12: false })}] ${message}`;
    setEvents((items) => [line, ...items.filter((item) => item !== "等待状态...")].slice(0, 80));
  }

  async function saveProxy() {
    if (!proxyDraft) return;
    setSaving(true);
    try {
      await api("/api/config", {
        method: "PUT",
        body: JSON.stringify({ proxy: normalizeProxyDraft(proxyDraft) }),
      });
      setProxyDraft(null);
      await refresh(true);
      pushEvent("代理策略已保存");
    } catch (error) {
      pushEvent(`保存代理策略失败: ${error.message}`);
    } finally {
      setSaving(false);
    }
  }

  async function addProvider(event) {
    event.preventDefault();
    setSaving(true);
    try {
      await api("/api/providers", {
        method: "POST",
        body: JSON.stringify({
          ...providerForm,
          sortIndex: Number(providerForm.sortIndex || 1),
          enabled: true,
          inFailoverQueue: true,
        }),
      });
      setProviderForm({ ...initialProviderForm, sortIndex: providers.length + 2 });
      await refresh(true);
      pushEvent(`已添加供应商: ${providerForm.name}`);
    } catch (error) {
      pushEvent(`添加供应商失败: ${error.message}`);
    } finally {
      setSaving(false);
    }
  }

  async function updateProvider(provider, patch) {
    try {
      await api(`/api/providers/${encodeURIComponent(provider.id)}`, {
        method: "PUT",
        body: JSON.stringify(patch),
      });
      await refresh(true);
      pushEvent(`供应商已更新: ${provider.name}`);
      return true;
    } catch (error) {
      pushEvent(`供应商更新失败: ${error.message}`);
      return false;
    }
  }

  async function loadProviderDetails(provider) {
    return api(`/api/providers/${encodeURIComponent(provider.id)}`);
  }

  async function providerAction(provider, action) {
    if (action === "delete" && !window.confirm(`确认删除供应商 ${provider.name}？`)) return;
    if (action === "test") {
      setProviderTestResults((items) => ({
        ...items,
        [provider.id]: {
          state: "pending",
          message: "正在等待模型回答...",
          startedAt: new Date().toISOString(),
        },
      }));
      pushEvent(`开始检测: ${provider.name}，等待模型回答...`);
    }
    try {
      const path = action === "delete"
        ? `/api/providers/${encodeURIComponent(provider.id)}`
        : `/api/providers/${encodeURIComponent(provider.id)}/${action}`;
      const result = await api(path, { method: action === "delete" ? "DELETE" : "POST" });
      await refresh(true);
      if (action === "test") {
        const message = result.message || (result.ok ? "模型回答正常" : "检测失败");
        setProviderTestResults((items) => ({
          ...items,
          [provider.id]: {
            state: result.ok ? "success" : "failed",
            ok: Boolean(result.ok),
            status: result.status,
            model: result.model,
            answer: result.answer,
            message,
            latencyMs: result.latencyMs,
            updatedAt: new Date().toISOString(),
          },
        }));
        pushEvent(`测试完成: ${provider.name} ${result.ok ? "正常" : "失败"}，${message}，延迟 ${result.latencyMs}ms`);
      } else {
        pushEvent(`供应商操作完成: ${provider.name}`);
      }
    } catch (error) {
      if (action === "test") {
        setProviderTestResults((items) => ({
          ...items,
          [provider.id]: {
            state: "failed",
            ok: false,
            message: error.message,
            updatedAt: new Date().toISOString(),
          },
        }));
      }
      pushEvent(`供应商操作失败: ${error.message}`);
    }
  }

  async function savePricing() {
    const payload = {};
    for (const row of pricing) {
      const model = row.model.trim();
      if (!model) continue;
      payload[model] = {
        inputPerMillion: Number(row.inputPerMillion || 0),
        outputPerMillion: Number(row.outputPerMillion || 0),
        cacheReadPerMillion: Number(row.cacheReadPerMillion || 0),
        cacheCreationPerMillion: Number(row.cacheCreationPerMillion || 0),
      };
    }
    try {
      await api("/api/billing/pricing", {
        method: "PUT",
        body: JSON.stringify({ pricing: payload }),
      });
      await refresh(true);
      pushEvent("计费价格已保存");
    } catch (error) {
      pushEvent(`保存计费价格失败: ${error.message}`);
    }
  }

  function openUsageDashboard(provider) {
    setUsageProviderFilter(provider ? { id: provider.id, name: provider.name } : null);
    setActiveView("billing");
  }

  return (
    <main className="cc-app">
      <header className="cc-header">
        <div className="header-left">
          <a className="brand-title" href="#providers" onClick={() => setActiveView("providers")}>
            CC Switch
          </a>
          <button className="icon-button" title="设置" onClick={() => setActiveView("settings")}>
            <Settings size={17} />
          </button>
          <button className="icon-button" title="使用统计" onClick={() => openUsageDashboard(null)}>
            <BarChart3 size={17} />
          </button>
        </div>

        <div className="header-center">
          <button className={`app-tab active`}>
            <span className="app-dot">AI</span>
            Codex
          </button>
          <button className="app-tab muted" disabled>Claude</button>
          <button className="app-tab muted" disabled>Gemini</button>
        </div>

        <div className="header-actions">
          <span className={`proxy-chip ${status?.running ? "ok" : "bad"}`}>
            <Server size={14} />
            {status?.running ? "本地代理运行中" : "代理检查中"}
          </span>
          <span className={`proxy-chip ${proxyDraft?.autoFailoverEnabled ? "ok" : ""}`}>
            <GitBranch size={14} />
            故障转移{proxyDraft?.autoFailoverEnabled ? "开启" : "关闭"}
          </span>
          <button className="button ghost" onClick={() => refresh()} disabled={loading}>
            {loading ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
          </button>
        </div>
      </header>

      <section className="cc-content">
        {activeView === "providers" && (
          <div className="providers-view">
            <section className="hero-strip">
              <div>
                <p className="eyebrow">Codex Provider Management</p>
                <h1>Lite CC Switch</h1>
                <p className="subtitle">服务器版 Web 管理台，保留 ccswitch 的供应商卡片、故障转移和使用统计体验。</p>
              </div>
              <button className="button" onClick={() => setActiveView("add")}>
                <Plus size={16} />
                添加供应商
              </button>
            </section>

            <section className="metric-grid compact">
              <Metric icon={<Server size={18} />} label="总请求" value={formatNumber(status?.totalRequests)} />
              <Metric icon={<CheckCircle2 size={18} />} label="成功率" value={`${Number(status?.successRate || 0).toFixed(1)}%`} />
              <Metric icon={<GitBranch size={18} />} label="故障转移" value={formatNumber(status?.failoverCount)} />
              <Metric icon={<Shield size={18} />} label="当前供应商" value={status?.currentProviderName || "未选择"} />
              <Metric icon={<Cpu size={18} />} label="本机 CPU" value={`${Number(status?.resources?.cpuPercent || 0).toFixed(1)}%`} />
              <Metric icon={<MemoryStick size={18} />} label="RSS 内存" value={formatMb(status?.resources?.memory?.rssMb)} />
              <Metric icon={<MemoryStick size={18} />} label="堆内存" value={`${formatMb(status?.resources?.memory?.heapUsedMb)} / ${formatMb(status?.resources?.memory?.heapTotalMb)}`} />
              <Metric icon={<Server size={18} />} label="进程 PID" value={status?.resources?.pid || "-"} />
            </section>

            <section className="provider-list-toolbar">
              <div className="provider-search">
                <Search size={15} />
                <input
                  value={providerSearch}
                  onChange={(event) => setProviderSearch(event.target.value)}
                  placeholder="搜索供应商、地址或备注..."
                />
                {providerSearch && (
                  <button type="button" onClick={() => setProviderSearch("")} title="清空搜索">
                    <X size={14} />
                  </button>
                )}
              </div>
              <div className="provider-list-meta">
                <span>{filteredProviders.length} / {providers.length} 个供应商</span>
                <span>{proxyDraft?.autoFailoverEnabled ? "故障转移模式" : "单供应商模式"}</span>
              </div>
            </section>

            <section className="provider-list">
              {filteredProviders.map((provider) => (
                <ProviderCard
                  key={provider.id}
                  provider={provider}
                  isCurrent={status?.currentProviderId === provider.id}
                  isAutoFailoverEnabled={proxyDraft?.autoFailoverEnabled}
                  billingStats={providerBillingByName.get(provider.name)}
                  testStatus={providerTestResults[provider.id]}
                  onUpdate={updateProvider}
                  onLoadDetails={loadProviderDetails}
                  onAction={providerAction}
                  onConfigureUsage={() => openUsageDashboard(provider)}
                />
              ))}
              {!providers.length && (
                <ProviderEmptyState
                  title="还没有供应商"
                  description="添加 ht、k1、k2 或新的 Codex 中转站后，本地代理才能开始转发请求。"
                  action="添加供应商"
                  onAction={() => setActiveView("add")}
                />
              )}
              {providers.length > 0 && !filteredProviders.length && (
                <ProviderEmptyState
                  title="没有匹配结果"
                  description="调整搜索关键词，或清空搜索后查看全部供应商。"
                  action="清空搜索"
                  onAction={() => setProviderSearch("")}
                />
              )}
            </section>
          </div>
        )}

        {activeView === "settings" && (
          <section className="two-column page-card">
            <article className="panel" id="strategy">
            <div className="panel-head">
              <PanelTitle title="代理策略" desc="修改后立即影响后续请求，正在进行的流式请求不会被打断。" />
              <button className="button" onClick={saveProxy} disabled={saving || !proxyDraft}>保存策略</button>
            </div>
            {proxyDraft && (
              <div className="form-grid">
                <Field label="自动故障转移">
                  <select value={String(proxyDraft.autoFailoverEnabled)} onChange={(e) => setProxyDraft({ ...proxyDraft, autoFailoverEnabled: e.target.value === "true" })}>
                    <option value="true">开启</option>
                    <option value="false">关闭</option>
                  </select>
                </Field>
                <NumberField label="单次最大尝试数" value={proxyDraft.maxAttempts} onChange={(value) => setProxyDraft({ ...proxyDraft, maxAttempts: value })} />
                <NumberField label="流式首包超时 ms" value={proxyDraft.streamingFirstByteTimeoutMs} onChange={(value) => setProxyDraft({ ...proxyDraft, streamingFirstByteTimeoutMs: value })} />
                <NumberField label="流式静默超时 ms" value={proxyDraft.streamingIdleTimeoutMs} onChange={(value) => setProxyDraft({ ...proxyDraft, streamingIdleTimeoutMs: value })} />
                <NumberField label="非流式总超时 ms" value={proxyDraft.nonStreamingTimeoutMs} onChange={(value) => setProxyDraft({ ...proxyDraft, nonStreamingTimeoutMs: value })} />
                <NumberField label="失败阈值" value={proxyDraft.circuit.failureThreshold} onChange={(value) => setProxyDraft({ ...proxyDraft, circuit: { ...proxyDraft.circuit, failureThreshold: value } })} />
                <NumberField label="恢复成功阈值" value={proxyDraft.circuit.successThreshold} onChange={(value) => setProxyDraft({ ...proxyDraft, circuit: { ...proxyDraft.circuit, successThreshold: value } })} />
                <NumberField label="打开后等待 ms" value={proxyDraft.circuit.openTimeoutMs} onChange={(value) => setProxyDraft({ ...proxyDraft, circuit: { ...proxyDraft.circuit, openTimeoutMs: value } })} />
                <NumberField label="错误率阈值 0-1" step="0.05" value={proxyDraft.circuit.errorRateThreshold} onChange={(value) => setProxyDraft({ ...proxyDraft, circuit: { ...proxyDraft.circuit, errorRateThreshold: value } })} />
                <NumberField label="最小请求数" value={proxyDraft.circuit.minRequests} onChange={(value) => setProxyDraft({ ...proxyDraft, circuit: { ...proxyDraft.circuit, minRequests: value } })} />
              </div>
            )}
            </article>

            <article className="panel">
            <PanelTitle title="添加供应商" desc="API Key 只写入本地配置，状态接口只返回掩码。" />
            <form className="provider-form" onSubmit={addProvider}>
              <TextField label="名称" value={providerForm.name} onChange={(value) => setProviderForm({ ...providerForm, name: value })} placeholder="例如：中转站 A" required />
              <TextField label="Base URL" value={providerForm.baseUrl} onChange={(value) => setProviderForm({ ...providerForm, baseUrl: value })} placeholder="https://example.com/v1" required />
              <TextField label="API Key" type="password" value={providerForm.apiKey} onChange={(value) => setProviderForm({ ...providerForm, apiKey: value })} placeholder="sk-..." required />
              <NumberField label="优先级" value={providerForm.sortIndex} onChange={(value) => setProviderForm({ ...providerForm, sortIndex: value })} />
              <TextField label="备注" value={providerForm.notes} onChange={(value) => setProviderForm({ ...providerForm, notes: value })} placeholder="额度、来源或说明" />
              <button className="button" type="submit" disabled={saving}>添加到队列</button>
            </form>
            </article>
          </section>
        )}

        {activeView === "add" && (
          <section className="page-card single">
            <article className="panel add-panel">
              <PanelTitle title="添加供应商" desc="API Key 只写入本地配置，状态接口只返回掩码。" />
              <form className="provider-form" onSubmit={addProvider}>
                <TextField label="名称" value={providerForm.name} onChange={(value) => setProviderForm({ ...providerForm, name: value })} placeholder="例如：中转站 A" required />
                <TextField label="Base URL" value={providerForm.baseUrl} onChange={(value) => setProviderForm({ ...providerForm, baseUrl: value })} placeholder="https://example.com/v1" required />
                <TextField label="API Key" type="password" value={providerForm.apiKey} onChange={(value) => setProviderForm({ ...providerForm, apiKey: value })} placeholder="sk-..." required />
                <NumberField label="优先级" value={providerForm.sortIndex} onChange={(value) => setProviderForm({ ...providerForm, sortIndex: value })} />
                <TextField label="备注" value={providerForm.notes} onChange={(value) => setProviderForm({ ...providerForm, notes: value })} placeholder="额度、来源或说明" />
                <button className="button" type="submit" disabled={saving}>添加到队列</button>
              </form>
            </article>
          </section>
        )}

        {activeView === "billing" && (
          <UsageDashboard
            billing={billing}
            logs={logs}
            providers={providers}
            providerFilter={usageProviderFilter}
            onProviderFilterChange={setUsageProviderFilter}
            pricing={pricing}
            setPricing={setPricing}
            onSavePricing={savePricing}
            onRefresh={() => refresh()}
          />
        )}

        <section className="panel log-panel">
          <PanelTitle title="事件日志" desc="展示当前网页管理台操作结果。" />
          <pre>{events.join("\n")}</pre>
        </section>
      </section>
    </main>
  );
}

function Metric({ icon, label, value }) {
  return (
    <article className="metric-card">
      <span>{icon}{label}</span>
      <strong>{value ?? "0"}</strong>
    </article>
  );
}

function formatMb(value) {
  const number = Number(value || 0);
  return `${number.toFixed(1)} MB`;
}

function ProviderEmptyState({ title, description, action, onAction }) {
  return (
    <article className="provider-empty-state">
      <div className="provider-empty-icon">
        <Server size={20} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      <button className="cc-button cc-button-primary" onClick={onAction}>
        <Plus size={15} />
        {action}
      </button>
    </article>
  );
}

function PanelTitle({ title, desc }) {
  return (
    <div>
      <h2>{title}</h2>
      <p>{desc}</p>
    </div>
  );
}

function Field({ label, children }) {
  return <label className="field"><span>{label}</span>{children}</label>;
}

function TextField({ label, value, onChange, type = "text", placeholder, required }) {
  return (
    <Field label={label}>
      <input type={type} value={value} placeholder={placeholder} required={required} onChange={(event) => onChange(event.target.value)} />
    </Field>
  );
}

function NumberField({ label, value, onChange, step = "1" }) {
  return (
    <Field label={label}>
      <input type="number" value={value ?? 0} step={step} onChange={(event) => onChange(Number(event.target.value))} />
    </Field>
  );
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  const response = await fetch(path, { ...options, headers });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(data?.error?.message || data?.message || `HTTP ${response.status}`);
  }
  return data;
}

function cloneProxy(proxy) {
  return proxy ? JSON.parse(JSON.stringify(proxy)) : null;
}

function normalizeProxyDraft(proxy) {
  return {
    ...proxy,
    maxAttempts: Number(proxy.maxAttempts || 1),
    streamingFirstByteTimeoutMs: Number(proxy.streamingFirstByteTimeoutMs || 60000),
    streamingIdleTimeoutMs: Number(proxy.streamingIdleTimeoutMs || 0),
    nonStreamingTimeoutMs: Number(proxy.nonStreamingTimeoutMs || 600000),
    circuit: {
      failureThreshold: Number(proxy.circuit?.failureThreshold || 4),
      successThreshold: Number(proxy.circuit?.successThreshold || 2),
      openTimeoutMs: Number(proxy.circuit?.openTimeoutMs || 60000),
      errorRateThreshold: Number(proxy.circuit?.errorRateThreshold || 0.6),
      minRequests: Number(proxy.circuit?.minRequests || 10),
    },
  };
}

function pricingToRows(pricing) {
  const rows = Object.entries(pricing || {}).map(([model, value]) => ({ model, ...value }));
  return rows.length ? rows : [{ model: "*", inputPerMillion: 0, outputPerMillion: 0, cacheReadPerMillion: 0, cacheCreationPerMillion: 0 }];
}

createRoot(document.getElementById("root")).render(<App />);
