# 定时任务迁移说明

## 更新概述

已将 CheerMate 插件的定时任务从旧的 `asyncio.create_task` 方式迁移到 AstrBot 新的 `CronJobManager` 系统，并采用 `active_agent` 方式。

## 技术选型：active_agent（已采用）

### active_agent 任务的优势
- **AI 驱动**: 由 AI 代理自动处理问候逻辑，无需手动调用 LLM
- **更好的 Prompt 遵循**: AI 代理的系统指令确保严格按照要求执行
- **自动化程度高**: 代理可以自主查看历史、生成内容、发送消息
- **灵活性强**: 可以根据上下文做出智能决策

### 为什么不用 basic 任务
- basic 任务需要手动调用 `llm_generate()`，存在 prompt 不遵循的问题
- 需要手动处理历史记录、消息发送等逻辑
- 代码复杂度更高

## 主要变更

### 1. 架构变化
**旧方式**: 单个定时任务 + 遍历用户列表
```python
# 一个任务处理所有用户
async def _start_scheduler(self):
    while True:
        await asyncio.sleep(wait_seconds)
        for user_id in self.subscribers:
            await self._send_daily_greeting(user_id)
```

**新方式**: 每个用户独立的 active_agent 任务
```python
# 每个用户一个独立的 AI 代理任务
for user_id in self.subscribers:
    job = await cron_mgr.add_active_job(
        name=f"CheerMate_Greeting_{user_id}",
        cron_expression=cron_expression,
        payload={
            "session": user_id,
            "note": "AI 代理的执行指令"
        }
    )
```

### 2. 问候语生成方式
**旧方式**: 手动调用 LLM
```python
async def _generate_personalized_greeting(self, user_id: str):
    # 手动获取历史
    conversation = await conv_mgr.get_conversation(user_id, curr_cid)
    # 手动构建 prompt
    prompt = self.greeting_prompt.format(...)
    # 手动调用 LLM
    llm_resp = await self.context.llm_generate(prompt=prompt)
```

**新方式**: AI 代理自动处理
```python
# 在 payload 的 note 中提供指令
note = """你是 CheerMate 陪伴机器人。现在是每天的问候时间。

请执行以下任务：
1. 查看用户最近的对话历史（最近 3 轮对话）
2. 根据历史内容，生成一条温暖、个性化的问候语
3. 直接发送问候消息给用户
"""
```

### 3. 订阅管理
**新方式**: 订阅/取消订阅时动态创建/删除定时任务
```python
# 订阅时创建任务
job = await cron_mgr.add_active_job(...)
self.cron_job_ids[user_id] = job.job_id

# 取消订阅时删除任务
await cron_mgr.remove_job(self.cron_job_ids[user_id])
```

### 4. 配置简化
**移除的配置**:
- `greeting_prompt`: 不再需要，AI 代理使用内置指令

**保留的配置**:
- `scheduled_time`: 推送时间
- `session_timeout`: 对话超时
- `praise_prompt`: 夸夸回复的提示词（手动触发时使用）

## 代码变化统计

- 删除代码: ~120 行（`_start_scheduler`, `_generate_personalized_greeting`, `_send_daily_greeting`）
- 新增代码: ~60 行（`_register_cron_jobs` 及订阅管理）
- 净减少: ~60 行代码

## 优势总结

1. **更可靠**: AI 代理的系统指令确保 prompt 严格遵循
2. **更简洁**: 代码量减少 50%，逻辑更清晰
3. **更智能**: AI 代理可以自主决策和处理
4. **持久化**: 任务存储在数据库，重启后自动恢复
5. **独立性**: 每个用户独立任务，互不影响

## 注意事项

- 确保 AstrBot 版本支持 `CronJobManager` 和 `active_agent`
- 每个订阅用户会创建一个独立的定时任务
- AI 代理会自动访问对话历史和发送消息工具
- 旧的 `greeting_prompt` 配置不再使用，可以从配置中移除
