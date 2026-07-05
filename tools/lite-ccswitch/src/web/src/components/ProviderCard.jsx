/**
 * 服务器版 ProviderCard。
 * 迁移 ccswitch 原版供应商卡片结构，保留拖拽手柄、供应商图标、故障转移优先级和 hover 操作区外观。
 */
import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, ChevronDown, ChevronUp, Eye, EyeOff, GripVertical, Loader2, Save, X, XCircle } from "lucide-react";
import { ProviderActions } from "./ProviderActions.jsx";
import { formatMoney, formatNumber, stateText } from "./format.js";

export function ProviderCard({
  provider,
  isCurrent,
  isAutoFailoverEnabled,
  billingStats,
  testStatus,
  onUpdate,
  onLoadDetails,
  onAction,
  onConfigureUsage,
}) {
  const [sortIndex, setSortIndex] = useState(provider.sortIndex || 1);
  const [expanded, setExpanded] = useState(false);
  const [editDraft, setEditDraft] = useState(() => providerToDraft(provider));
  const [editError, setEditError] = useState("");
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isSummaryKeyVisible, setIsSummaryKeyVisible] = useState(false);
  const [summaryApiKey, setSummaryApiKey] = useState("");
  const [isEditKeyVisible, setIsEditKeyVisible] = useState(false);
  const circuit = provider.circuit || {};
  const circuitClass = circuit.state === "open" ? "bad" : circuit.state === "half_open" ? "warn" : "ok";
  const displayUrl = provider.baseUrl || provider.notes || "未配置接口地址";

  useEffect(() => {
    setSortIndex(provider.sortIndex || 1);
  }, [provider.sortIndex]);

  useEffect(() => {
    setExpanded(false);
    setEditDraft(providerToDraft(provider));
    setEditError("");
    setIsSummaryKeyVisible(false);
    setSummaryApiKey("");
    setIsEditKeyVisible(false);
  }, [provider.id]);

  const usageLine = useMemo(() => {
    if (!billingStats) return "暂无用量";
    return `${formatNumber(billingStats.totalTokens)} Tokens · ${formatMoney(billingStats.estimatedCostUsd, 4)}`;
  }, [billingStats]);

  return (
    <article className={`cc-provider-card group ${isCurrent ? "active" : ""}`}>
      <div className="active-gradient" />
      <div className="provider-row-main">
        <div className="provider-main-left">
          <button className="drag-handle" aria-label="拖拽排序">
            <GripVertical size={16} />
          </button>

          <div className="provider-avatar">AI</div>

          <div className="provider-identity">
            <div className="provider-name-row">
              <h3>{provider.name}</h3>
              {provider.inFailoverQueue && (
                <span className="priority-badge">P{provider.sortIndex || 1}</span>
              )}
              {isCurrent && <span className="state-pill ok">使用中</span>}
              <span className={`state-pill ${circuitClass}`}>
                {stateText(circuit.state)}
              </span>
            </div>

            <button
              className="provider-url"
              type="button"
              title={displayUrl}
              onClick={() => displayUrl.startsWith("http") && window.open(displayUrl, "_blank", "noreferrer")}
            >
              <span>{displayUrl}</span>
            </button>
          </div>
        </div>

        <div className="provider-main-right">
          <div className="usage-mini">
            <strong>{usageLine}</strong>
            <small className="api-key-summary">
              <span>Key: {isSummaryKeyVisible ? summaryApiKey : provider.apiKeyMasked || "未设置"}</span>
              {provider.hasApiKey && (
                <button type="button" title={isSummaryKeyVisible ? "隐藏 API Key" : "显示 API Key"} onClick={toggleSummaryKey}>
                  {isSummaryKeyVisible ? <EyeOff size={13} /> : <Eye size={13} />}
                </button>
              )}
            </small>
          </div>

          <div className="provider-actions-wrap">
            <ProviderActions
              isCurrent={isCurrent}
              isTesting={testStatus?.state === "pending"}
              isAutoFailoverEnabled={isAutoFailoverEnabled}
              isInFailoverQueue={provider.inFailoverQueue}
              onSwitch={() => onAction(provider, "select")}
              onEdit={toggleEditor}
              onDuplicate={() => duplicateProvider(provider)}
              onTest={() => onAction(provider, "test")}
              onConfigureUsage={onConfigureUsage}
              onResetCircuit={() => onAction(provider, "reset")}
              onDelete={() => onAction(provider, "delete")}
              onToggleFailover={(enabled) => onUpdate(provider, { inFailoverQueue: enabled })}
            />
          </div>
        </div>
      </div>

      {testStatus && (
        <div className={`provider-test-status ${testStatus.state}`}>
          <div className="provider-test-title">
            {testStatus.state === "pending" ? (
              <Loader2 className="spin" size={14} />
            ) : testStatus.state === "success" ? (
              <CheckCircle2 size={14} />
            ) : (
              <XCircle size={14} />
            )}
            <span>{testStatus.state === "pending" ? "正在等待返回" : testStatus.state === "success" ? "检测成功" : "检测失败"}</span>
          </div>
          <p>{testStatus.message || "无返回消息"}</p>
          <small>
            {testStatus.model ? `模型 ${testStatus.model}` : "模型检测"}
            {testStatus.latencyMs ? ` · ${testStatus.latencyMs}ms` : ""}
            {testStatus.status ? ` · 上游 ${testStatus.status}` : ""}
          </small>
          {testStatus.attempts?.length > 1 && (
            <small className="provider-model-line">
              尝试链路：{testStatus.attempts.map((item) => `${item.model}${item.ok ? "✓" : `(${item.status || "失败"})`}`).join(" -> ")}
            </small>
          )}
        </div>
      )}

      <ModelSupportSummary support={provider.modelSupport} />

      <div className="provider-inline-controls">
        <label>
          <input
            type="checkbox"
            checked={provider.enabled}
            onChange={(event) => onUpdate(provider, { enabled: event.target.checked })}
          />
          启用
        </label>
        <label>
          <input
            type="checkbox"
            checked={provider.inFailoverQueue}
            onChange={(event) => onUpdate(provider, { inFailoverQueue: event.target.checked })}
          />
          加入故障转移
        </label>
        <label className="sort-control">
          优先级
          <input
            type="number"
            min="1"
            value={sortIndex}
            onChange={(event) => setSortIndex(event.target.value)}
            onBlur={() => onUpdate(provider, { sortIndex: Number(sortIndex || 1) })}
          />
        </label>
        <button className="expand-button" type="button" onClick={toggleEditor}>
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          编辑
        </button>
      </div>

      {expanded && (
        <form className="provider-editor" onSubmit={saveDraft}>
          <div className="provider-editor-head">
            <div>
              <h4>供应商配置</h4>
              <p>直接修改本地队列中的供应商配置，保存后立即影响后续请求。</p>
            </div>
            <div className="provider-editor-actions">
              <button className="cc-button cc-button-secondary cc-button-sm" type="button" onClick={() => setExpanded(false)}>
                <X size={14} />
                取消
              </button>
              <button className="cc-button cc-button-primary cc-button-sm" type="submit" disabled={isLoadingDetails || isSavingDraft}>
                {isSavingDraft ? <Loader2 className="spin" size={14} /> : <Save size={14} />}
                保存配置
              </button>
            </div>
          </div>

          {editError && <div className="provider-edit-error">{editError}</div>}

          {isLoadingDetails ? (
            <div className="provider-editor-loading">
              <Loader2 className="spin" size={16} />
              正在读取原始配置...
            </div>
          ) : (
            <>
              <div className="provider-editor-grid">
                <label>
                  <span>名称</span>
                  <input value={editDraft.name} onChange={(event) => updateDraft("name", event.target.value)} />
                </label>
                <label>
                  <span>Base URL</span>
                  <input value={editDraft.baseUrl} onChange={(event) => updateDraft("baseUrl", event.target.value)} placeholder="https://example.com/v1" />
                </label>
                <label>
                  <span>API Key</span>
                  <div className="api-key-input">
                    <input
                      type="text"
                      value={isEditKeyVisible ? editDraft.apiKey : maskSecret(editDraft.apiKey)}
                      readOnly={!isEditKeyVisible}
                      onChange={(event) => updateDraft("apiKey", event.target.value)}
                      placeholder="sk-..."
                    />
                    <button type="button" title={isEditKeyVisible ? "隐藏 API Key" : "显示 API Key"} onClick={() => setIsEditKeyVisible((value) => !value)}>
                      {isEditKeyVisible ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </label>
                <label>
                  <span>优先级</span>
                  <input type="number" min="1" value={editDraft.sortIndex} onChange={(event) => updateDraft("sortIndex", event.target.value)} />
                </label>
              </div>

              <div className="provider-editor-switches">
                <label>
                  <input type="checkbox" checked={editDraft.enabled} onChange={(event) => updateDraft("enabled", event.target.checked)} />
                  启用
                </label>
                <label>
                  <input type="checkbox" checked={editDraft.inFailoverQueue} onChange={(event) => updateDraft("inFailoverQueue", event.target.checked)} />
                  加入故障转移队列
                </label>
                <span>熔断失败 / 请求：{circuit.consecutiveFailures || 0} / {circuit.totalRequests || 0}</span>
                <span>计费请求：{billingStats?.requests || 0}</span>
              </div>

              <label className="provider-editor-field">
                <span>备注</span>
                <textarea rows="2" value={editDraft.notes} onChange={(event) => updateDraft("notes", event.target.value)} />
              </label>

              <div className="provider-editor-grid advanced">
                <label>
                  <span>模型映射 JSON</span>
                  <textarea rows="6" value={editDraft.modelMapText} onChange={(event) => updateDraft("modelMapText", event.target.value)} placeholder={'{\n  "gpt-5.5": "real-upstream-model"\n}'} />
                </label>
                <label>
                  <span>自定义请求头 JSON</span>
                  <textarea rows="6" value={editDraft.customHeadersText} onChange={(event) => updateDraft("customHeadersText", event.target.value)} placeholder={'{\n  "x-provider": "value"\n}'} />
                </label>
              </div>

              <label className="provider-editor-field">
                <span>剥离参数</span>
                <textarea rows="3" value={editDraft.stripParamsText} onChange={(event) => updateDraft("stripParamsText", event.target.value)} placeholder={"parallel_tool_calls\nstore"} />
              </label>
            </>
          )}
        </form>
      )}
    </article>
  );

  async function toggleEditor() {
    if (expanded) {
      setExpanded(false);
      return;
    }
    setExpanded(true);
    setEditError("");
    setIsLoadingDetails(Boolean(onLoadDetails));
    try {
      const details = onLoadDetails ? await onLoadDetails(provider) : provider;
      setEditDraft(providerToDraft(details));
      setIsEditKeyVisible(false);
    } catch (error) {
      setEditError(`读取原始配置失败: ${error.message}`);
      setEditDraft(providerToDraft(provider));
    } finally {
      setIsLoadingDetails(false);
    }
  }

  async function toggleSummaryKey() {
    if (isSummaryKeyVisible) {
      setIsSummaryKeyVisible(false);
      return;
    }
    try {
      const details = onLoadDetails ? await onLoadDetails(provider) : provider;
      setSummaryApiKey(details.apiKey || "");
      setIsSummaryKeyVisible(true);
    } catch (error) {
      setEditError(`读取 API Key 失败: ${error.message}`);
    }
  }

  function updateDraft(key, value) {
    setEditDraft((draft) => ({ ...draft, [key]: value }));
  }

  async function saveDraft(event) {
    event.preventDefault();
    setEditError("");
    let modelMap;
    let customHeaders;
    try {
      modelMap = parseJsonObject(editDraft.modelMapText, "模型映射 JSON");
      customHeaders = parseJsonObject(editDraft.customHeadersText, "自定义请求头 JSON");
    } catch (error) {
      setEditError(error.message);
      return;
    }
    setIsSavingDraft(true);
    try {
      const ok = await onUpdate(provider, {
        name: editDraft.name,
        baseUrl: editDraft.baseUrl,
        apiKey: editDraft.apiKey,
        enabled: editDraft.enabled,
        inFailoverQueue: editDraft.inFailoverQueue,
        sortIndex: Number(editDraft.sortIndex || 1),
        notes: editDraft.notes,
        modelMap,
        customHeaders,
        stripParams: parseList(editDraft.stripParamsText),
      });
      if (ok !== false) {
        setExpanded(false);
      }
    } finally {
      setIsSavingDraft(false);
    }
  }

  function duplicateProvider(source) {
    const text = `${source.name}\n${source.baseUrl}\n${source.notes || ""}`;
    navigator.clipboard?.writeText(text).catch(() => {});
  }
}

function providerToDraft(source) {
  return {
    name: source?.name || "",
    baseUrl: source?.baseUrl || "",
    apiKey: source?.apiKey || "",
    enabled: Boolean(source?.enabled ?? true),
    inFailoverQueue: Boolean(source?.inFailoverQueue ?? true),
    sortIndex: source?.sortIndex || 1,
    notes: source?.notes || "",
    modelMapText: JSON.stringify(source?.modelMap || {}, null, 2),
    customHeadersText: JSON.stringify(source?.customHeaders || {}, null, 2),
    stripParamsText: Array.isArray(source?.stripParams) ? source.stripParams.join("\n") : "",
  };
}

function ModelSupportSummary({ support }) {
  const supported = support?.supportedModels || [];
  const unsupported = support?.unsupportedModels || [];
  const preferred = support?.preferredTestModel || "";
  if (!supported.length && !unsupported.length && !preferred) return null;
  return (
    <div className="provider-model-support">
      {preferred && <span>检测模型：{preferred}</span>}
      {supported.length > 0 && <span>支持：{supported.join("、")}</span>}
      {unsupported.length > 0 && <span>不支持：{unsupported.join("、")}</span>}
    </div>
  );
}

function maskSecret(value) {
  const text = String(value || "");
  if (!text) return "";
  if (text.length <= 8) return text;
  return `${text.slice(0, 4)}••••${text.slice(-4)}`;
}

function parseJsonObject(value, label) {
  const text = String(value || "").trim();
  if (!text) return {};
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error(`${label} 不是合法 JSON`);
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label} 必须是对象`);
  }
  return parsed;
}

function parseList(value) {
  return String(value || "")
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}
