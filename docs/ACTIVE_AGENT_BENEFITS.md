# 为什么使用 active_agent 而不是 basic 任务

## 问题背景

在旧实现中，使用 `context.llm_generate()` 手动调用 LLM 生成问候语时，存在以下问题：

1. **Prompt 不遵循**: LLM 有时不按照 prompt 要求回答
2. **需要手动处理**: 需要手动获取历史、构建 prompt、调用 LLM、发送消息
3. **代码复杂**: 大量的错误处理和降级逻辑

## active_agent 的解决方案

### 核心优势

1. **AI 代理的系统指令更可靠**
   - AI 代理有专门的系统 prompt（`PROACTIVE_AGENT_CRON_WOKE_SYSTEM_PROMPT`）
   - 系统指令的优先级高于普通 prompt
   - 代理被明确告知要执行定时任务

2. **自动化程度高**
   - 代理自动访问对话历史（通过工具）
   - 代理自动生成内容
   - 代理自动发送消息（使用 `send_message_to_user` 工具）

3. **代码更简洁**
   - 只需提供任务描述（note）
   - 无需手动调用 LLM
   - 无需手动处理消息发送

### 工作流程对比

#### 旧方式（手动 LLM 调用）
```
插件 → 获取历史 → 构建 prompt → 调用 llm_generate() → 解析结果 → 发送消息
     ↓ 可能出错                  ↓ prompt 可能不遵循      ↓ 需要降级处理
```

#### 新方式（active_agent）
```
CronJobManager → 唤醒 AI 代理 → 代理自动执行任务
                              ↓
                    - 查看历史（工具）
                    - 生成问候语（AI）
                    - 发送消息（工具）
```

## 实际效果

### 任务描述（note）
```python
note = """你是 CheerMate 陪伴机器人。现在是每天的问候时间（22:00）。

请执行以下任务：
1. 查看用户最近的对话历史（最近 3 轮对话）
2. 根据历史内容，生成一条温暖、个性化的问候语
3. 问候语要求：
   - 自然、温暖、像朋友一样
   - 如果有历史记录，结合用户最近的状态或话题
   - 如果没有历史记录，使用通用但温暖的问候
   - 鼓励用户分享今天的感受或小成就
   - 长度控制在 50 字以内

请直接发送问候消息给用户，不要询问是否发送。"""
```

### AI 代理的执行
1. 代理收到系统指令：这是一个定时任务，需要执行
2. 代理读取 note：了解具体要做什么
3. 代理调用工具：查看对话历史
4. 代理生成内容：基于历史生成个性化问候
5. 代理调用工具：发送消息给用户

## 为什么比 basic 任务更好

### basic 任务的局限
```python
# basic 任务仍然需要手动调用 LLM
async def _send_daily_greeting(self):
    for user_id in self.subscribers:
        # 还是要手动调用 llm_generate()
        llm_resp = await self.context.llm_generate(prompt=prompt)
        # 还是会遇到 prompt 不遵循的问题
```

### active_agent 的优势
- 每个用户独立的 AI 代理任务
- 代理有明确的系统指令和上下文
- 代理可以使用工具（查看历史、发送消息）
- 更符合 AstrBot 的设计理念

## 总结

使用 `active_agent` 是解决 "LLM 不按 prompt 回答" 问题的最佳方案：
- ✅ 系统指令优先级更高
- ✅ 代理自动化处理所有逻辑
- ✅ 代码更简洁、更可靠
- ✅ 符合 AstrBot 官方推荐的最佳实践
