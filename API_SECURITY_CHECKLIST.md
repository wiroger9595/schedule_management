# 🔐 API 密鑰安全恢復清單

## ⚠️ 問題發現
您的 API 密鑰已暴露在 Git 代碼中：
- ✗ `server/.env` - Cerebras, Groq, Gemini, Cloudinary, Line, LangSmith 密鑰
- ✗ `server/.env-dev` - 相同密鑰
- ✗ `server/.env-prod` - 相同密鑰
- ✗ Git 歷史中存儲了敏感信息

## 🎯 立即操作清單

### Step 1: 撤銷所有舊密鑰 ❌
要防止任何人利用已暴露的密鑰，**必須立即撤銷**：

#### 1.1 Cerebras API
- 去: https://console.cerebras.ai/api-keys
- 找到密鑰: `csk-k9rdhh348jxf4f2t9ddyce9xnmdphyhycmkfkr92ej82m3wt`
- 點擊 Delete / Revoke
- ✅ **生成新密鑰**並複製

#### 1.2 Groq API
- 去: https://console.groq.com/keys
- 找到密鑰: `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`
- 點擊 Delete / Revoke
- ✅ **生成新密鑰**並複製

#### 1.3 Gemini API
- 去: https://aistudio.google.com/app/apikey
- 找到密鑰: `AIzaSyDwHBk_PzTFpA4WcFb3ktqKT69B4HaYrBs`
- 點擊 Delete
- ✅ **生成新密鑰**並複製

#### 1.4 其他暴露的密鑰
- ✗ OpenRouter: `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`
- ✗ Cloudflare: `cfut_wb4yPTytcfTmlA9PfxMg8rqiuoHDtdP53fVKFgQ03c9011d8`
- ✗ LangSmith: `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`
- ✗ Line Channel Token / Secret
- ✗ Database Password (Supabase)
- ✗ Redis Password (Upstash)
- ✗ SECRET_KEY (JWT)

**動作**: 在相應服務控制台撤銷所有上述密鑰

---

### Step 2: 將新密鑰添加到 .env.local ✅

編輯 `server/.env.local`：
```bash
nano server/.env.local
```

填入您從各服務獲得的新密鑰：
```
CEREBRAS_API_KEY=<paste_new_key_from_cerebras_console>
GROQ_API_KEY=<paste_new_key_from_groq_console>
GEMINI_API_KEY=<paste_new_key_from_aistudio>
OPENROUTER_API_KEY=<paste_new_key>
CLOUDFLARE_API_TOKEN=<paste_new_token>
LANGCHAIN_API_KEY=<paste_new_key>
```

---

### Step 3: 驗證 .gitignore 已設置 ✅

確認 `.gitignore` 包含：
```
.env.local
.env.*-local
server/.env.local
server/.env.*-local
```

檢查命令：
```bash
grep -E "\.env|secret|key|credentials" .gitignore
```

---

### Step 4: 從 Git 歷史中移除敏感信息 ⚠️

⚠️ **選項 A: 清理歷史（推薦）**
```bash
# 方案 1: 重寫歷史（謹慎操作）
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch server/.env server/.env-dev server/.env-prod' \
  --prune-empty -- --all

# 推送強制更新（警告：會影響協作者）
git push --force origin main
```

⚠️ **選項 B: 只是標記（如果無法重寫歷史）**
```bash
# 添加評論說明敏感信息已撤銷
git log --oneline | head -1
# 然後創建新提交說明
```

---

### Step 5: 驗證密鑰已生效 ✅

在更新 `.env.local` 後，重新加載環境變數：
```bash
cd /Users/chenrobert/Documents/code_life/schedule_management
source server/.env.local

# 驗證環境變數
echo "Cerebras: ${CEREBRAS_API_KEY:0:20}..."
echo "Groq: ${GROQ_API_KEY:0:20}..."
echo "Gemini: ${GEMINI_API_KEY:0:20}..."
```

---

### Step 6: 重新跑測試 🚀

確認新密鑰可用：
```bash
cd /Users/chenrobert/Documents/code_life/schedule_management
python3 optimize_ai_quick_demo.py
```

預期結果：
- ✅ 如果看到實際 API 響應（不是 "rate limited"）
- ✅ 測試應該開始通過
- ✅ 回到之前的改善驗證

---

## 📋 檢查清單

- [ ] 1.1 撤銷 Cerebras 舊密鑰並生成新密鑰
- [ ] 1.2 撤銷 Groq 舊密鑰並生成新密鑰
- [ ] 1.3 撤銷 Gemini 舊密鑰並生成新密鑰
- [ ] 1.4 撤銷其他暴露的密鑰（OpenRouter, Cloudflare, LangSmith, Line, DB, Redis）
- [ ] 2 將新密鑰添加到 `server/.env.local`
- [ ] 3 驗證 `.gitignore` 已配置
- [ ] 4 清理 Git 歷史（可選但推薦）
- [ ] 5 驗證環境變數加載成功
- [ ] 6 重新跑測試並確認成功

---

## 🛡️ 未來最佳實踐

1. **永遠不要**將密鑰提交到 Git
2. **只在** `.env.local` 存儲敏感信息
3. **定期輪換** API 密鑰（每 3-6 個月）
4. **監控** API 使用量避免超限
5. **使用** `pre-commit` 鉤子防止意外提交密鑰

### 設置 Pre-commit 鉤子
```bash
cd /Users/chenrobert/Documents/code_life/schedule_management

# 創建防止提交密鑰的鉤子
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
if git diff --cached | grep -E "(CEREBRAS_API_KEY|GROQ_API_KEY|GEMINI_API_KEY|password|secret)" | grep -v ".env.local"; then
  echo "❌ 檢測到密鑰在提交中！"
  echo "提示: 不要提交 .env、.env-dev、.env-prod 中的密鑰"
  exit 1
fi
EOF

chmod +x .git/hooks/pre-commit
```

---

## 💡 需要幫助？

- Cerebras: https://console.cerebras.ai
- Groq: https://console.groq.com
- Gemini: https://aistudio.google.com
- Git 歷史清理: https://git-scm.com/docs/git-filter-branch
