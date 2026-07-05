# MinerU 鉴权文件说明

本目录用于存放 MinerU API 的鉴权信息。这里面的内容很敏感，别拿去公开仓库乱飞，不然等于主动给自己找事。

建议至少做到：

- `active.json` / `1.md` 只给当前用户读写
- 如果后续纳入 git，务必继续忽略真实 token 文件
- 优先维护 `keys/active.json`，旧的 `tokens/1.md` 只做兼容

## 推荐格式

默认优先读取：

- `keys/active.json`

示例结构见：

- `keys/active.sample.json`

字段含义：

- `bearer_jwt`：用于 `Authorization: Bearer ...`
- `user_token`：用于请求头 `token`
- `created_at_utc` / `expires_at_utc`：便于人工检查有效期
- `valid_days`：便于确认 token 生命周期

## 兼容旧格式

若你手头只有一行 JWT，也可以放在：

- `tokens/1.md`

工具会自动兼容，但这种格式就是临时凑合，维护性明显更差。
