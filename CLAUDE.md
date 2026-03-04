# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CheerMate is an AstrBot plugin that provides emotional support through AI-powered affirmations. It sends scheduled daily greetings (default: 22:00) using AstrBot's `CronJobManager` with `active_agent` type tasks, and generates warm, unconditional positive responses to user inputs.

**Core Concept**: Transform "small achievements" into meaningful progress through value reframing ("watched 2 pages of a book" → "persisted in learning after a full day of work").

**Key Features**:
- Daily greetings via `active_agent` cron jobs — AI agent reads conversation history and generates personalized greetings automatically
- Per-user independent cron jobs, persistent across restarts
- Multi-round supportive conversations
- Natural timeout handling (silent end, no intrusive messages)

## Development Commands

### Running the Plugin
This plugin runs within AstrBot, not standalone:
```bash
# 1. Clone to AstrBot's plugin directory
cd AstrBot/data/plugins/
git clone https://github.com/warrior-dl/astrbot_plugin_cheer_mate.git

# 2. Enable plugin in AstrBot WebUI
# 3. Configure via WebUI settings
```

### No Testing Framework
Currently no test suite exists. Manual testing via AstrBot chat interface.

## Architecture

### Single-File Plugin Structure
- **main.py**: Complete plugin implementation
- **CheerMatePlugin** class: Inherits from `astrbot.api.star.Star`

### Core Components

#### 1. Scheduled Task System (CronJobManager)
- Uses `context.cron_manager.add_active_job()` to register per-user cron jobs
- Each subscriber gets an independent `active_agent` task
- `cron_job_ids` (dict: user_id → job_id) persisted via KV storage
- On `initialize()`: cleans up old persisted jobs, re-registers all
- On `terminate()`: deletes all jobs, clears persisted data
- Cron expression built from `scheduled_time` config: `f"{minute} {hour} * * *"`

#### 2. active_agent Task Execution
- AstrBot's `CronJobManager` wakes a main agent at trigger time
- Agent receives `note` (task instruction from `greeting_prompt`) as the task description
- Agent automatically loads user's conversation history and persona via `_get_session_conv`
- Agent uses `send_message_to_user` tool to deliver the greeting
- No manual LLM calls needed — the agent handles everything

#### 3. Subscription Management
- Subscribers stored as `Set[str]` of user IDs (unified_msg_origin format)
- Persisted via KV storage: `get_kv_data("subscribers")` / `put_kv_data("subscribers")`
- `cron_job_ids` also persisted: `get_kv_data("cron_job_ids")` / `put_kv_data("cron_job_ids")`
- Subscribe: creates cron job → saves job_id
- Unsubscribe: deletes cron job → removes job_id

#### 4. Multi-Round Conversation
- Uses AstrBot's `session_waiter` decorator with `SessionController`
- 60-second timeout per response (configurable via `session_timeout`)
- Graceful exit keywords: ["没了", "谢谢", "结束", "不说了", "就这样", "拜拜"]
- Timeout behavior: silent end (no message sent)

#### 5. AI Reply Generation (praise)
- LLM call via `context.llm_generate(chat_provider_id, prompt, timeout=30)`
- Prompt customizable via `praise_prompt` config
- Fallback: pre-defined random replies if LLM fails

### Configuration System
Config schema in `_conf_schema.json`:
- `scheduled_time`: Daily greeting time (HH:MM format)
- `session_timeout`: Seconds to wait for user reply
- `greeting_prompt`: Task instruction for the AI agent (supports `{scheduled_time}`). Describes *what to do*, not *who to be* — persona is managed by AstrBot's persona system
- `praise_prompt`: Custom prompt for praise replies (supports `{user_input}`)

## Key AstrBot Patterns

### CronJobManager — active_agent
```python
cron_mgr = self.context.cron_manager

# Register
job = await cron_mgr.add_active_job(
    name=f"CheerMate_Greeting_{user_id}",
    cron_expression="0 22 * * *",
    payload={
        "session": user_id,       # unified_msg_origin
        "sender_id": "system",
        "note": "task instruction",
        "origin": "plugin_cheermate"
    },
    description="...",
    persistent=True,
    enabled=True
)
job_id = job.job_id

# Delete
await cron_mgr.delete_job(job_id)
```

### KV Persistence
```python
# Load
data = await self.get_kv_data("key", default_value)

# Save
await self.put_kv_data("key", data)
```

### Event Handlers
```python
@filter.command("command_name", alias={"中文别名1", "别名2"})
async def handler(self, event: AstrMessageEvent):
    yield event.plain_result("response text")
```

### LLM Integration (for praise replies)
```python
provider_id = await self.context.get_current_chat_provider_id(event.unified_msg_origin)
llm_resp = await self.context.llm_generate(
    chat_provider_id=provider_id,
    prompt=self.praise_prompt.format(user_input=user_input),
    timeout=30
)
reply = llm_resp.completion_text.strip()
```

### Session Control
```python
@session_waiter(timeout=60, record_history_chains=False)
async def conversation_handler(controller: SessionController, event: AstrMessageEvent):
    user_input = event.message_str.strip()
    controller.stop()                              # end
    controller.keep(timeout=60, reset_timeout=True)  # continue
```

## Important Implementation Details

### Persona and History in active_agent
The `active_agent` cron job automatically:
1. Loads user's conversation via `_get_session_conv`
2. Injects conversation history into context
3. Loads persona via `_ensure_persona_and_skills` (global default)

Therefore, `greeting_prompt` should only describe the task ("what to do"), not the persona ("who to be"). Persona is configured in AstrBot's persona management UI.

### Cron Job Lifecycle
```
initialize()
  → _cleanup_old_cron_jobs()   # delete persisted job_ids from last run
  → _register_cron_jobs()      # re-create for all subscribers
  → _save_cron_job_ids()       # persist new job_ids

subscribe()
  → add_active_job()
  → _save_cron_job_ids()

unsubscribe()
  → delete_job()
  → _save_cron_job_ids()

reload_greeting()              # after greeting_prompt config change
  → delete_job()
  → add_active_job()           # with updated note
  → _save_cron_job_ids()

terminate()
  → delete_job() for all
  → put_kv_data("cron_job_ids", {})
```

### Payload Structure
```python
payload = {
    "session": user_id,        # unified_msg_origin, required by _woke_main_agent
    "sender_id": "system",
    "note": greeting_prompt,   # task instruction for the agent
    "origin": "plugin_cheermate"
}
```

## Logging
```python
from astrbot.api import logger
logger.info(f"[CheerMate] Message")
logger.warning(f"[CheerMate] Warning")
logger.error(f"[CheerMate] Error: {e}")
```
