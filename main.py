"""
AI Friend - 陪伴机器人插件
一个温暖的陪伴插件，在你焦虑时无条件肯定你
"""
import os
import asyncio
from datetime import datetime, time
from pathlib import Path
from typing import Dict, Set

from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from astrbot.core.utils.session_waiter import session_waiter, SessionController


@register(
    "AI Friend - 陪伴机器人",
    "AI Friend Team",
    "一个温暖的陪伴插件，在你焦虑时无条件肯定你。每天晚上主动问候，通过AI高情商回复提供情绪价值。",
    "0.1.0",
    "https://github.com/yourusername/ai-friend"
)
class AIFriendPlugin(Star):
    """AI陪伴机器人插件"""

    def __init__(self, context: Context, config: dict):
        super().__init__(context)

        # 读取配置
        self.scheduled_time = config.get("scheduled_time", "22:00")
        self.reply_style = config.get("reply_style", "balanced")
        self.max_rounds = config.get("max_conversation_rounds", 3)
        self.session_timeout = config.get("session_timeout", 60)

        # 订阅用户列表（用户ID集合）
        self.subscribers: Set[str] = set()

        # 定时任务
        self.scheduler_task = None

        # Prompt 模板路径
        self.plugin_dir = Path(__file__).parent
        self.prompts_dir = self.plugin_dir / "prompts"

        logger.info(f"[AI Friend] 插件初始化完成")
        logger.info(f"[AI Friend] 配置: 推送时间={self.scheduled_time}, 风格={self.reply_style}")

        # 加载订阅列表
        asyncio.create_task(self._load_subscribers())

        # 启动定时任务
        asyncio.create_task(self._start_scheduler())

    async def _load_subscribers(self):
        """从存储加载订阅用户列表"""
        try:
            data = await self.get_kv_data("subscribers", [])
            self.subscribers = set(data)
            logger.info(f"[AI Friend] 已加载 {len(self.subscribers)} 个订阅用户")
        except Exception as e:
            logger.error(f"[AI Friend] 加载订阅列表失败: {e}")

    async def _save_subscribers(self):
        """保存订阅用户列表到存储"""
        try:
            await self.put_kv_data("subscribers", list(self.subscribers))
            logger.info(f"[AI Friend] 订阅列表已保存")
        except Exception as e:
            logger.error(f"[AI Friend] 保存订阅列表失败: {e}")

    async def _start_scheduler(self):
        """启动定时任务"""
        logger.info(f"[AI Friend] 定时任务已启动，推送时间: {self.scheduled_time}")

        while True:
            try:
                # 计算下次触发时间
                now = datetime.now()
                hour, minute = map(int, self.scheduled_time.split(":"))
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

                # 如果今天的时间已过，设置为明天
                if target_time <= now:
                    from datetime import timedelta
                    target_time += timedelta(days=1)

                # 计算等待时间
                wait_seconds = (target_time - now).total_seconds()
                logger.info(f"[AI Friend] 下次推送时间: {target_time}, 等待 {wait_seconds:.0f} 秒")

                # 等待到触发时间
                await asyncio.sleep(wait_seconds)

                # 执行推送
                await self._send_daily_greeting()

                # 等待1分钟，避免重复触发
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"[AI Friend] 定时任务异常: {e}")
                # 出错后等待5分钟再重试
                await asyncio.sleep(300)

    async def _send_daily_greeting(self):
        """向所有订阅用户发送每日问候"""
        if not self.subscribers:
            logger.info(f"[AI Friend] 无订阅用户，跳过推送")
            return

        logger.info(f"[AI Friend] 开始向 {len(self.subscribers)} 个用户推送问候")

        # 问候语列表（随机选择）
        greetings = [
            "嘿，今天感觉怎么样？有没有做什么让你觉得还不错的事？哪怕很小的一件~",
            "今天辛苦啦！有什么想和我分享的吗？",
            "嘿！今天有什么小成就想告诉我吗？",
            "忙了一天了，今天有没有哪怕一件微不足道的小事让你觉得还不错？",
        ]

        import random
        greeting = random.choice(greetings)

        # 向每个订阅用户推送
        success_count = 0
        for user_id in list(self.subscribers):
            try:
                # 构建消息链
                chain = MessageChain().message(greeting)

                # 发送消息（私聊）
                # 这里需要构建 unified_msg_origin
                # 格式: platform_type:user_id
                umo_str = user_id

                # 发送消息
                await self.context.send_message(umo_str, chain)
                success_count += 1
                logger.info(f"[AI Friend] 成功推送给用户: {user_id}")

                # 避免发送过快
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"[AI Friend] 推送给 {user_id} 失败: {e}")

        logger.info(f"[AI Friend] 推送完成: 成功 {success_count}/{len(self.subscribers)}")

    async def _load_prompt_template(self, style: str) -> str:
        """加载指定风格的 Prompt 模板"""
        try:
            prompt_file = self.prompts_dir / f"{style}.txt"
            if prompt_file.exists():
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.warning(f"[AI Friend] Prompt 文件不存在: {prompt_file}，使用默认模板")
                return self._get_default_prompt()
        except Exception as e:
            logger.error(f"[AI Friend] 加载 Prompt 失败: {e}")
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """获取默认 Prompt 模板"""
        return """你是一个温暖、无条件支持用户的陪伴机器人"小确幸"。

【核心原则】
1. 无条件肯定：无论用户说做了什么，都要找到值得肯定的点
2. 价值重构：将"小事"重新定义为"进步"
3. 具体化鼓励：使用数字、对比、具体场景让肯定更有力量
4. 给予许可：明确告诉用户"你已经做得很好了，可以安心休息"

【回复风格】
- 语气：温暖、真诚、略带俏皮
- 长度：2-3句话
- 结构：肯定 + 重构 + 许可

现在，用户对你说：

"{user_input}"

请给出你的回复（2-3句话，温暖且具体）："""

    async def _generate_praise_reply(self, user_input: str, event: AstrMessageEvent) -> str:
        """
        生成夸夸回复

        Args:
            user_input: 用户输入
            event: 消息事件

        Returns:
            AI生成的回复文本
        """
        try:
            # 加载 Prompt 模板
            prompt_template = await self._load_prompt_template(self.reply_style)

            # 填充用户输入
            prompt = prompt_template.replace("{user_input}", user_input)

            # 获取当前聊天的 provider_id
            umo = event.unified_msg_origin
            provider_id = await self.context.get_current_chat_provider_id(umo)

            if not provider_id:
                logger.error(f"[AI Friend] 无法获取 provider_id")
                return self._get_fallback_reply(user_input)

            # 调用 LLM 生成回复
            logger.info(f"[AI Friend] 调用 LLM 生成回复...")
            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=prompt,
                timeout=30
            )

            if llm_resp and llm_resp.completion_text:
                reply = llm_resp.completion_text.strip()
                logger.info(f"[AI Friend] AI回复生成成功")
                return reply
            else:
                logger.warning(f"[AI Friend] LLM 返回空回复")
                return self._get_fallback_reply(user_input)

        except Exception as e:
            logger.error(f"[AI Friend] 生成回复失败: {e}")
            return self._get_fallback_reply(user_input)

    def _get_fallback_reply(self, user_input: str) -> str:
        """获取降级回复（LLM失败时使用）"""
        fallback_replies = [
            "听到你的分享我很开心！今天的你已经很棒了，好好休息吧~",
            "你做得已经很好了！每一点进步都值得被看见，安心去休息吧。",
            "太好了！能坚持到现在已经很不容易了，今天的你也在发光呢✨",
            "这已经很不错了！你的努力都被看见了，可以安心结束今天了。",
        ]
        import random
        return random.choice(fallback_replies)

    @filter.command("开启陪伴")
    async def subscribe(self, event: AstrMessageEvent):
        """订阅每日问候"""
        # 获取用户ID
        user_id = event.unified_msg_origin

        if user_id in self.subscribers:
            yield event.plain_result(f"你已经订阅了每日陪伴~\n每天 {self.scheduled_time} 我会来问候你！")
            return

        # 添加到订阅列表
        self.subscribers.add(user_id)
        await self._save_subscribers()

        reply = f"订阅成功！🌟\n\n每天 {self.scheduled_time}，我会主动问候你：\n\"今天感觉怎么样？有什么想分享的吗？\"\n\n如果不想收到推送，发送 /关闭陪伴 即可取消~"
        yield event.plain_result(reply)

        logger.info(f"[AI Friend] 用户 {user_id} 订阅成功")

    @filter.command("关闭陪伴")
    async def unsubscribe(self, event: AstrMessageEvent):
        """取消订阅每日问候"""
        user_id = event.unified_msg_origin

        if user_id not in self.subscribers:
            yield event.plain_result("你还没有订阅每日陪伴哦~\n发送 /开启陪伴 即可订阅！")
            return

        # 从订阅列表移除
        self.subscribers.remove(user_id)
        await self._save_subscribers()

        reply = "已取消订阅。\n如果想再次开启，随时发送 /开启陪伴~"
        yield event.plain_result(reply)

        logger.info(f"[AI Friend] 用户 {user_id} 取消订阅")

    @filter.command("夸夸我")
    async def praise_me(self, event: AstrMessageEvent):
        """手动触发夸夸对话"""
        yield event.plain_result("今天做了什么想和我分享的吗？")

        # 启动对话会话
        await self._start_conversation(event)

    @filter.command("今日总结")
    async def daily_summary(self, event: AstrMessageEvent):
        """今日总结（夸夸我的别名）"""
        yield event.plain_result("来说说今天的收获吧，哪怕是很小的一件事~")

        # 启动对话会话
        await self._start_conversation(event)

    async def _start_conversation(self, event: AstrMessageEvent, round_count: int = 1):
        """
        启动对话会话

        Args:
            event: 消息事件
            round_count: 当前轮数
        """
        @session_waiter(timeout=self.session_timeout, record_history_chains=False)
        async def conversation_handler(controller: SessionController, event: AstrMessageEvent):
            user_input = event.message_str.strip()

            # 检查是否要结束对话
            end_keywords = ["没了", "谢谢", "结束", "不说了", "就这样", "拜拜"]
            if any(keyword in user_input for keyword in end_keywords):
                goodbye_msg = "好的！今天辛苦啦，晚安~ 🌙"
                await event.send(event.plain_result(goodbye_msg))
                controller.stop()
                return

            # 生成AI回复
            ai_reply = await self._generate_praise_reply(user_input, event)
            await event.send(event.plain_result(ai_reply))

            # 检查是否达到最大轮数
            if round_count >= self.max_rounds:
                final_msg = "今天的分享就到这里吧，你已经很棒了！早点休息，明天见~ ✨"
                await event.send(event.plain_result(final_msg))
                controller.stop()
                return

            # 继续对话
            follow_up = "还有其他想分享的吗？"
            await event.send(event.plain_result(follow_up))

            # 继续等待下一轮
            controller.keep(timeout=self.session_timeout, reset_timeout=True)

        try:
            await conversation_handler(event)
        except asyncio.TimeoutError:
            # 超时处理
            timeout_msg = "看来你已经去休息了~ 累了就早点睡，晚安！🌙"
            await event.send(event.plain_result(timeout_msg))
        except Exception as e:
            logger.error(f"[AI Friend] 对话异常: {e}")
            error_msg = "抱歉，遇到了一些问题... 你可以稍后再试试~"
            await event.send(event.plain_result(error_msg))
