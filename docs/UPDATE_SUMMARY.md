# 更新总结 - 支持自定义每日问候 Prompt

## 更新内容

已添加对每日问候 prompt 的自定义配置支持，用户可以完全控制 AI 代理的问候行为。

## 新增功能

### 1. 可配置的 greeting_prompt

在插件配置中的 `greeting_prompt` 字段：
- 默认值：包含完整的默认 AI 代理指令
- 自定义：直接修改配置文本即可
- 支持变量：`{scheduled_time}`

### 2. 新增命令：/重载问候

```
/reload_greeting
/重载问候
/更新问候配置
```

修改 `greeting_prompt` 配置后，使用此命令更新定时任务，无需重启插件。

## 工作原理

### greeting_prompt 的作用

`greeting_prompt` 不是问候语本身，而是发给 AI 代理的任务指令。

**流程**:
```
定时触发 → AI 代理收到指令 → 代理执行任务
                              ↓
                    - 查看对话历史
                    - 生成个性化问候
                    - 发送消息给用户
```

### 为什么这样设计

1. **更可靠**: AI 代理的系统指令优先级高，严格遵循
2. **更灵活**: 可以指示代理做任何合理的任务
3. **更智能**: 代理可以自主决策和处理

## 使用示例

### 默认指令（留空时使用）

```
你是 CheerMate 陪伴机器人。现在是每天的问候时间（22:00）。

请执行以下任务：
1. 查看用户最近的对话历史（最近 3 轮对话）
2. 根据历史内容，生成一条温暖、个性化的问候语
3. 问候语要求：
   - 自然、温暖、像朋友一样
   - 如果有历史记录，结合用户最近的状态或话题
   - 如果没有历史记录，使用通用但温暖的问候
   - 鼓励用户分享今天的感受或小成就
   - 长度控制在 50 字以内

请直接发送问候消息给用户，不要询问是否发送。
```

### 自定义示例 1：简短风格

```
你是 CheerMate。现在是 {scheduled_time}，该问候用户了。

任务：
1. 查看最近 2 轮对话
2. 生成一句简短的问候（20 字以内）
3. 直接发送，不要询问

风格：简洁、温暖、口语化
```

### 自定义示例 2：特定场景

```
你是 CheerMate 陪伴机器人。现在是晚上 {scheduled_time}，用户可能刚结束一天的工作。

任务：
1. 查看用户今天的对话（如果有）
2. 生成一条关心用户的晚安问候
3. 重点关注：
   - 用户今天是否提到了压力或困难
   - 用户是否分享了开心的事
   - 如果没有对话，使用温暖的通用问候

问候风格：像朋友一样关心，给予情绪支持

直接发送问候，不要询问。
```

## 配置更新流程

1. 在 AstrBot WebUI 中修改 `greeting_prompt`
2. 保存配置
3. 发送命令：`/重载问候`
4. 系统会删除旧任务并创建新任务
5. 下次定时触发时使用新配置

## 技术实现

### 代码变更

1. **添加配置读取**
```python
self.greeting_prompt = config.get("greeting_prompt", "")
```

2. **添加 note 构建方法**
```python
def _build_greeting_note(self) -> str:
    return self.greeting_prompt.format(scheduled_time=self.scheduled_time)
```

3. **添加重载命令**
```python
@filter.command("reload_greeting", alias={"重载问候", "更新问候配置"})
async def reload_greeting(self, event: AstrMessageEvent):
    # 删除旧任务
    # 创建新任务（使用最新配置）
```

### 配置文件更新

在 `_conf_schema.json` 中添加：
```json
{
  "greeting_prompt": {
    "description": "每日问候 AI 代理指令",
    "type": "text",
    "default": "你是 CheerMate 陪伴机器人...",
    "hint": "支持变量: {scheduled_time}"
  }
}
```

## 文档更新

新增文档：
- `docs/GREETING_PROMPT_GUIDE.md` - 详细的 prompt 编写指南

更新文档：
- `docs/USER_GUIDE.md` - 添加配置说明和使用技巧
- `docs/COMMANDS.md` - 添加新命令说明
- `docs/MIGRATION_TO_CRONJOBMANAGER.md` - 更新迁移说明

## 优势

1. **完全可控**: 用户可以完全控制问候的风格和内容
2. **开箱即用**: 默认配置已包含完整指令，无需额外设置
3. **灵活性高**: 可以根据不同场景定制不同的指令
4. **易于更新**: 通过命令即时更新，无需重启

## 注意事项

1. **这是 AI 代理指令，不是问候语本身**
   - 代理会根据指令自动生成问候语
   - 不要直接写"你好"之类的问候语

2. **使用清晰的指令**
   - 明确告诉代理要做什么
   - 提供具体的要求和示例
   - 强调执行方式（如"直接发送"）

3. **测试你的配置**
   - 修改后使用 `/重载问候` 更新
   - 可以等待下次定时触发测试
   - 或者查看 AstrBot 的定时任务管理界面

## 相关资源

- [GREETING_PROMPT_GUIDE.md](./GREETING_PROMPT_GUIDE.md) - 详细的编写指南
- [ACTIVE_AGENT_BENEFITS.md](./ACTIVE_AGENT_BENEFITS.md) - 为什么使用 active_agent
- [MIGRATION_TO_CRONJOBMANAGER.md](./MIGRATION_TO_CRONJOBMANAGER.md) - 迁移说明
