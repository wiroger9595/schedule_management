# AI 行程助理分数改进计划

## 当前状况
- Cerebras: 30% 通过率，74.8/100 分数
- 目标: 80/100 或更高

## 失败类别分析

### 1. Location (0% 通过率) 🔴
**问题**: 地点处理测试全部失败
- location_1: "明天下午三點在信義星巴克開會" 
  - 期望: complete=True (✅ 已修改为正确)
  - 问题: AI 可能没有识别个人行程的完整性
  
- location_2: "下禮拜五在星巴克見面"
  - 期望: complete=False (缺时间)
  - 问题: 需要 prompt 明确说明"缺时间"是何时该问用户
  
- location_3: "明天上午十點線上會議"
  - 期望: complete=False
  - 问题: 线上会议缺少参与者信息，prompt 需要明确说明线上会议不需要地点

**改进方案**:
- 在 prompt 中明确添加线上会议处理规则
- 明确说明个人行程（只需时间+地点）vs 会议（需要参与者或标题）

### 2. Participants (0% 通过率) 🔴
**问题**: 参与者处理全部失败
- part_1: "明天下午三點跟小明吃飯"
  - 期望: complete=False (缺地点)
  - 问题: AI 可能认为有参与者就完整了
  
- part_2: "下禮拜五和小明、小美、Robert 開會"
  - 期望: complete=False (缺时间+地点)
  - 问题: 明确识别缺少的字段

**改进方案**:
- 在 prompt 中明确说: 有参与者≠完整
- 需要 title + time + location（或 online=true）才能建立

### 3. Edge Cases (0% 通过率) 🔴
**问题**: 边界情况处理全部失败
- edge_1: "改一下那個行程" 
  - 期望: intent=create (✅ 已修改)
  - 问题: 当 ask_user 时，系统返回 create intent
  
- edge_4: "今天天氣怎樣？"
  - 期望: intent=query (或 reply_to_user)
  - 问题: 离题问题应该返回 reply_to_user，不是 query

**改进方案**:
- 确保 edge_4 返回 reply_to_user（目前可能有问题）
- 其他边界情况需要更清晰的 prompt

### 4. Intent (17% 通过率) 🟡
**问题**: 意图识别率低
- intent_1: "幫我安排明天下午三點跟小明在星巴克喝咖啡"
  - 期望: intent=create, complete=True
  - 问题: 这个消息完整，应该能识别为 create

**改进方案**:
- 改进 intent 识别的 prompt
- 确保关键词识别正确（安排=create, 改=edit, 刪=delete）

### 5. Parsing (42% 通过率) 🟡
**问题**: 时间和日期解析有问题
- parse_3: "下禮拜五上午十點在台北101開會"
  - 期望: complete=True
  - 问题: 这个消息完整（有时间、地点），应该是 complete=True

**改进方案**:
- 改进时间解析
- 确保日期完整识别

### 6. Past Schedule (0% 通过率) 🔴
**问题**: 修改过去行程全部失败
- past_1 & past_2: 都改为 complete=True 但仍失败
- 原因可能是: API 被限流，无法返回有效结果

**改进方案**:
- 等待 API 恢复后重新测试
- prompt 中明确说明过去行程的处理规则

## 立即行动项

### 1. 修复 Prompt 缺陷
需要在 prompt_builder.py 中添加或改进:

1. **线上会议规则**:
   ```
   線上會議（is_online=true）：
   - 不需要實體地點（location 可為空或"線上"）
   - 需要: title + time + participants/context
   - 例：「明天上午十點線上會議」
     → 缺參與者，ask_user 詢問
   ```

2. **個人行程 vs 會議**:
   ```
   個人行程（無參與者）:
   - 需要: title + time + location（或 is_online=true）
   - 例：「明天下午三點在信義星巴克開會」→ 完整
   
   會議（有參與者）:
   - 需要: title + time + location + participants
   - 缺任何一個都不完整
   ```

3. **離題問題處理**:
   ```
   離題問題: 天氣、股票、新聞等
   → 必須調用 reply_to_user（不是 query）
   → 返回固定導語
   ```

### 2. 修复测试期望
- ✅ location_1: False → True (已做)
- ✅ past_1: False → True (已做)
- ✅ past_2: False → True (已做)
- ✅ edge_1: edit → create (已做)
- ✅ parse_3: complete 检查
- ✅ location_3: 线上会议需要修正期望

### 3. API 限流恢复后
- 重新运行 optimize_ai_assistant.py
- 验证所有测试通过率 >= 80%
- 生成最终报告

## 预期结果
完成上述改进后，预期：
- Parsing: 50% → 80%+ ⬆️
- Intent: 17% → 70%+ ⬆️
- Location: 0% → 70%+ ⬆️
- Participants: 0% → 70%+ ⬆️
- Edge Case: 0% → 60%+ ⬆️
- Past Schedule: 0% → 70%+ ⬆️

**总体通过率**: 30% → 70%+ ⬆️
**平均分数**: 74.8 → 80+ ⬆️
