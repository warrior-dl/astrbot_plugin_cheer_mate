"""
CheerMate - 陪伴机器人插件
一个温暖的陪伴插件，在你焦虑时无条件肯定你
"""
import os
import asyncio
import json
import random
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Dict, Set

from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from astrbot.core.utils.session_waiter import session_waiter, SessionController


@register(
    "CheerMate - 陪伴夸夸机器人",
    "warrior-dl",
    "一个温暖的陪伴插件，在你焦虑时无条件肯定你。每天晚上主动问候，通过AI回复提供情绪价值。",
    "0.1.1",
    "https://github.com/warrior-dl/astrbot_plugin_cheer_mate"
)
class CheerMatePlugin(Star):
    """AI陪伴机器人插件"""

    def __init__(self, context: Context, config: dict):
        super().__init__(context)

        # 读取配置
        self.scheduled_time = self._validate_time_format(config.get("scheduled_time", "22:00"))
        self.session_timeout = config.get("session_timeout", 60)

        # 读取自定义提示词
        self.greeting_prompt = config.get("greeting_prompt", "")
        self.praise_prompt = config.get("praise_prompt", "")

        # 订阅用户列表（用户ID集合）
        self.subscribers: Set[str] = set()

        # 定时任务
        self.scheduler_task = None

        logger.info(f"[CheerMate] 插件初始化完成")
        logger.info(f"[CheerMate] 配置: 推送时间={self.scheduled_time}")

    def _validate_time_format(self, time_str: str) -> str:
        """
        验证时间格式是否为 HH:MM
        
        Args:
            time_str: 时间字符串
            
        Returns:
            验证后的时间字符串，如果格式错误则返回默认值 "22:00"
        """
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                raise ValueError("时间格式必须为 HH:MM")
            
            hour = int(parts[0])
            minute = int(parts[1])
            
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("小时必须在 0-23 之间，分钟必须在 0-59 之间")
            
            return time_str
        except Exception as e:
            logger.warning(f"[CheerMate] 时间格式错误 '{time_str}': {e}，使用默认值 '22:00'")
            return "22:00"

    async def initialize(self):
        """初始化插件，启动定时任务"""
        # 加载订阅列表
        await self._load_subscribers()
        
        # 启动定时任务（保存任务引用）
        self.scheduler_task = asyncio.create_task(self._start_scheduler())
        
        logger.info(f"[CheerMate] 插件启动成功，已加载 {len(self.subscribers)} 个订阅用户")

    async def _load_subscribers(self):
        """从存储加载订阅用户列表"""
        try:
            data = await self.get_kv_data("subscribers", [])
            self.subscribers = set(data)
            logger.info(f"[CheerMate] 已加载 {len(self.subscribers)} 个订阅用户")
        except Exception as e:
            logger.error(f"[CheerMate] 加载订阅列表失败: {e}")

    async def _save_subscribers(self):
        """保存订阅用户列表到存储"""
        try:
            await self.put_kv_data("subscribers", list(self.subscribers))
            logger.info(f"[CheerMate] 订阅列表已保存")
        except Exception as e:
            logger.error(f"[CheerMate] 保存订阅列表失败: {e}")

    async def _start_scheduler(self):
        """启动定时任务"""
        logger.info(f"[CheerMate] 定时任务已启动，推送时间: {self.scheduled_time}")
        
        last_push_date = None  # 记录上次推送的日期

        while True:
            try:
                # 计算下次触发时间
                now = datetime.now()
                hour, minute = map(int, self.scheduled_time.split(":"))
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

                # 如果今天的时间已过，设置为明天
                if target_time <= now:
                    target_time += timedelta(days=1)

                # 计算等待时间
                wait_seconds = (target_time - now).total_seconds()
                logger.info(f"[CheerMate] 下次推送时间: {target_time}, 等待 {wait_seconds:.0f} 秒")

                # 等待到触发时间
                await asyncio.sleep(wait_seconds)

                # 检查今天是否已经推送过
                today = datetime.now().date()
                if last_push_date == today:
                    logger.warning(f"[CheerMate] 今天已推送过，跳过本次推送")
                    await asyncio.sleep(60)
                    continue

                # 执行推送
                await self._send_daily_greeting()
                last_push_date = today

                await asyncio.sleep(3600)

            except Exception as e:
                logger.error(f"[CheerMate] 定时任务异常: {e}")
                # 出错后等待5分钟再重试
                await asyncio.sleep(300)

    async def _send_daily_greeting(self):
        """向所有订阅用户发送每日问候"""
        if not self.subscribers:
            logger.info(f"[CheerMate] 无订阅用户，跳过推送")
            return

        logger.info(f"[CheerMate] 开始向 {len(self.subscribers)} 个用户推送问候")

        # 向每个订阅用户推送
        success_count = 0
        for user_id in list(self.subscribers):
            try:
                # 生成个性化问候语（基于历史对话）
                greeting = await self._generate_personalized_greeting(user_id)

                # 构建消息链
                chain = MessageChain().message(greeting)

                # 发送消息
                await self.context.send_message(user_id, chain)
                success_count += 1
                logger.info(f"[CheerMate] 成功推送给用户: {user_id}")

                # 避免发送过快
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"[CheerMate] 推送给 {user_id} 失败: {e}")

        logger.info(f"[CheerMate] 推送完成: 成功 {success_count}/{len(self.subscribers)}")

    async def _generate_personalized_greeting(self, user_id: str) -> str:
        """
        基于历史对话生成个性化问候语

        Args:
            user_id: 用户ID (unified_msg_origin格式)

        Returns:
            个性化问候语文本
        """
        try:
            # 1. 获取对话历史
            conv_mgr = self.context.conversation_manager
            curr_cid = await conv_mgr.get_curr_conversation_id(user_id)
            conversation = await conv_mgr.get_conversation(user_id, curr_cid)

            if not conversation or not conversation.history:
                # 新用户或无历史，使用默认问候语
                logger.info(f"[CheerMate] 用户 {user_id} 无历史记录，使用默认问候语")
                return self._get_default_greeting()

            # 2. 解析历史记录
            if not conversation.history or not isinstance(conversation.history, str):
                logger.info(f"[CheerMate] 用户 {user_id} 历史记录为空或格式错误，使用默认问候语")
                return self._get_default_greeting()
            
            messages = json.loads(conversation.history)

            if not messages:
                logger.info(f"[CheerMate] 用户 {user_id} 历史为空，使用默认问候语")
                return self._get_default_greeting()

            # 3. 只取最近 3-5 条对话（最近3轮）
            recent_messages = messages[-6:] if len(messages) >= 6 else messages

            # 4. 构建历史文本
            history_text = ""
            for msg in recent_messages:
                role = "用户" if msg.get("role") == "user" else "你"
                content = msg.get("content", "")
                history_text += f"{role}: {content}\n"

            # 5. 构建 Prompt（直接使用配置中的提示词）
            prompt = self.greeting_prompt.format(
                scheduled_time=self.scheduled_time,
                history_text=history_text
            )
            logger.debug(f"[CheerMate] 个性化问候 Prompt:\n{prompt}")

            # 6. 调用 LLM 生成
            provider_id = await self.context.get_current_chat_provider_id(user_id)

            if not provider_id:
                logger.warning(f"[CheerMate] 无法获取用户 {user_id} 的 provider_id，使用默认问候语")
                return self._get_default_greeting()

            logger.info(f"[CheerMate] 正在为用户 {user_id} 生成个性化问候语...")
            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=prompt,
                timeout=30
            )

            if llm_resp and llm_resp.completion_text:
                personalized_greeting = llm_resp.completion_text.strip()
                logger.info(f"[CheerMate] 个性化问候语生成成功")
                return personalized_greeting
            else:
                logger.warning(f"[CheerMate] LLM 返回空回复，使用默认问候语")
                return self._get_default_greeting()

        except Exception as e:
            logger.error(f"[CheerMate] 生成个性化问候语失败: {e}")
            return self._get_default_greeting()

    def _get_default_greeting(self) -> str:
        """获取默认问候语（随机选择）"""
        greetings = [
            "嘿，今天感觉怎么样？有没有做什么让你觉得还不错的事？哪怕很小的一件~",
            "今天辛苦啦！有什么想和我分享的吗？",
            "嘿！今天有什么小成就想告诉我吗？",
            "忙了一天了，今天有没有哪怕一件微不足道的小事让你觉得还不错？",
        ]
        return random.choice(greetings)

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
            # 构建 Prompt（直接使用配置中的提示词）
            prompt = self.praise_prompt.format(user_input=user_input)
            logger.debug(f"[CheerMate] 夸夸回复 Prompt:\n{prompt}")

            # 获取当前聊天的 provider_id
            umo = event.unified_msg_origin
            provider_id = await self.context.get_current_chat_provider_id(umo)

            if not provider_id:
                logger.error(f"[CheerMate] 无法获取 provider_id")
                return self._get_fallback_reply(user_input)

            # 调用 LLM 生成回复
            logger.info(f"[CheerMate] 调用 LLM 生成回复...")
            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=prompt,
                timeout=30
            )

            if llm_resp and llm_resp.completion_text:
                reply = llm_resp.completion_text.strip()
                logger.info(f"[CheerMate] AI回复生成成功")
                return reply
            else:
                logger.warning(f"[CheerMate] LLM 返回空回复")
                return self._get_fallback_reply(user_input)

        except Exception as e:
            logger.error(f"[CheerMate] 生成回复失败: {e}")
            return self._get_fallback_reply(user_input)

    def _get_fallback_reply(self, user_input: str) -> str:
        """获取降级回复（LLM失败时使用）"""
        fallback_replies = [
            "听到你的分享我很开心！今天的你已经很棒了，好好休息吧~",
            "你做得已经很好了！每一点进步都值得被看见，安心去休息吧。",
            "太好了！能坚持到现在已经很不容易了，今天的你也在发光呢✨",
            "这已经很不错了！你的努力都被看见了，可以安心结束今天了。",
        ]
        return random.choice(fallback_replies)

    @filter.command("subscribe", alias={"开启陪伴", "订阅"})
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

        logger.info(f"[CheerMate] 用户 {user_id} 订阅成功")

    @filter.command("unsubscribe", alias={"关闭陪伴", "取消订阅"})
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

        logger.info(f"[CheerMate] 用户 {user_id} 取消订阅")

    @filter.command("praise", alias={"夸夸我", "夸我"})
    async def praise_me(self, event: AstrMessageEvent):
        """手动触发夸夸对话"""
        yield event.plain_result("今天做了什么想和我分享的吗？")

        # 启动对话会话
        await self._start_conversation(event)

    @filter.command("clear_history", alias={"清空历史", "重置对话"})
    async def clear_history(self, event: AstrMessageEvent):
        """清空当前用户的对话历史（修改 prompt 配置后使用）"""
        user_id = event.unified_msg_origin

        try:
            conv_mgr = self.context.conversation_manager
            curr_cid = await conv_mgr.get_curr_conversation_id(user_id)
            await conv_mgr.clear_conversation(user_id, curr_cid)

            reply = "对话历史已清空！✨\n下次对话将使用最新的 prompt 配置。"
            yield event.plain_result(reply)
            logger.info(f"[CheerMate] 用户 {user_id} 清空了对话历史")

        except Exception as e:
            logger.error(f"[CheerMate] 清空对话历史失败: {e}")
            yield event.plain_result("清空失败，请稍后重试~")

    async def _start_conversation(self, event: AstrMessageEvent):
        """
        启动对话会话

        Args:
            event: 消息事件
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

            # 继续对话
            follow_up = "还有其他想分享的吗？"
            await event.send(event.plain_result(follow_up))

            # 继续等待下一轮
            controller.keep(timeout=self.session_timeout, reset_timeout=True)

        try:
            await conversation_handler(event)
        except asyncio.TimeoutError:
            # 超时静默结束，不发送消息
            logger.info(f"[CheerMate] 对话超时，静默结束")
        except Exception as e:
            logger.error(f"[CheerMate] 对话异常: {e}")
            error_msg = "抱歉，遇到了一些问题... 你可以稍后再试试~"
            await event.send(event.plain_result(error_msg))

    async def terminate(self):
        """插件卸载时的清理方法（AstrBot 标准生命周期方法）"""
        logger.info(f"[CheerMate] 开始清理插件资源...")
        
        # 取消定时任务
        if self.scheduler_task and not self.scheduler_task.done():
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                logger.info(f"[CheerMate] 定时任务已取消")
            except Exception as e:
                logger.error(f"[CheerMate] 取消定时任务时出错: {e}")
        
        logger.info(f"[CheerMate] 插件资源清理完成")
