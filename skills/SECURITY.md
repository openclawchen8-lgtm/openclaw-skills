# Security Policy | 安全原則

## 🔒 基本原則：嚴禁包含敏感資訊

本仓库的所有文件（`*.md`、`*.json`、`*.sh`、`*.py`、`*.yaml` 等）**嚴禁**包含以下任何內容：

| 類別 | 範例 |
|------|------|
| 🔑 API Key / Token | `sk-or-v1-xxx`、`ghp_xxx`、`ghs_xxx`、`OPENAI_API_KEY` |
| 🔑 Bot Token | Telegram Bot Token、`TG_BOT_TOKEN` |
| 🔑 登入憑證 | 使用者名稱、密碼、帳號 |
| 🔑 私人金鑰 | SSH Private Key、Certificate |
| 🔑 內部 Endpoint | 僅供內網存取的 URL（含內網 IP） |
| 🔑 個人身份資訊 | 真實姓名、身分證號、手機號碼 |

## ✅ 正確做法

**使用佔位符**（`<>` 包裹）替代真實值：

```json
{
  "telegram_bot_token": "<YOUR_TELEGRAM_BOT_TOKEN>",
  "apiKey": "<YOUR_OPENROUTER_API_KEY>"
}
```

**禁止**使用以下形式的佔位符（因格式與真實金鑰相同，易被誤用）：
- ❌ `YOUR_BOT_TOKEN`（無 `<>` 包裹）
- ❌ `sk-or-v1-xxxxxxxxxxxx`（摻雜在說明中的實例格式）
- ❌ `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## 🛡️ 發布前檢查清單

上傳前請確認：

```bash
# 掃描所有文件
grep -rli "ghp_\|ghs_\|ghu_\|gho_\|sk-\|sk--\|ghp_\|Bearer\|api.key\|apikey\|api_key\|secret\|password\s*=" --include="*.md" --include="*.json" --include="*.yaml" .
```

發現任何匹配 → **立即置換為佔位符**後再提交。

## 🚨 若發現敏感資訊外洩

請立即：
1. 撤銷該 API Key / Token（GitHub 本身不應儲存任何金鑰）
2. 重新生成新的 Key
3. 儘快提交修正版本

---

*本原則適用於所有 ClawHub 發布的 Skill 及其相關文件。*
