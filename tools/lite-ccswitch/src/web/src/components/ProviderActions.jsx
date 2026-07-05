/**
 * 服务器版 ProviderActions。
 * 迁移 ccswitch 原版按钮布局，动作改为调用父组件提供的 HTTP API 适配函数。
 */
import {
  Activity,
  BarChart3,
  Check,
  Copy,
  Edit,
  Loader2,
  Play,
  Plus,
  RotateCcw,
  Trash2,
} from "lucide-react";

export function ProviderActions({
  isCurrent,
  isTesting = false,
  isAutoFailoverEnabled = false,
  isInFailoverQueue = false,
  onSwitch,
  onEdit,
  onDuplicate,
  onTest,
  onConfigureUsage,
  onResetCircuit,
  onDelete,
  onToggleFailover,
}) {
  const mainText = isAutoFailoverEnabled
    ? isInFailoverQueue
      ? "已加入"
      : "加入"
    : isCurrent
      ? "使用中"
      : "启用";
  const MainIcon = isAutoFailoverEnabled && !isInFailoverQueue ? Plus : isCurrent ? Check : Play;

  function handleMainClick() {
    if (isAutoFailoverEnabled && onToggleFailover) {
      onToggleFailover(!isInFailoverQueue);
      return;
    }
    if (!isCurrent) onSwitch();
  }

  return (
    <div className="provider-actions">
      <span className={isCurrent && !isAutoFailoverEnabled ? "cursor-disabled" : ""}>
        <button
          className={`cc-button cc-button-sm ${isCurrent && !isAutoFailoverEnabled ? "cc-button-muted" : "cc-button-primary"}`}
          onClick={handleMainClick}
          disabled={isCurrent && !isAutoFailoverEnabled}
        >
          <MainIcon size={15} />
          {mainText}
        </button>
      </span>

      <div className="provider-icon-actions">
        <button className="cc-icon-action" onClick={onEdit} title="编辑">
          <Edit size={15} />
        </button>
        <button className="cc-icon-action" onClick={onDuplicate} title="复制">
          <Copy size={15} />
        </button>
        <button className="cc-icon-action" onClick={onTest} disabled={isTesting} title="检测连通">
          {isTesting ? <Loader2 className="spin" size={15} /> : <Activity size={15} />}
        </button>
        <button className="cc-icon-action" onClick={onConfigureUsage} title="使用统计">
          <BarChart3 size={15} />
        </button>
        <button className="cc-icon-action" onClick={onResetCircuit} title="重置熔断">
          <RotateCcw size={15} />
        </button>
        <button className="cc-icon-action danger" onClick={onDelete} title="删除">
          <Trash2 size={15} />
        </button>
      </div>
    </div>
  );
}
