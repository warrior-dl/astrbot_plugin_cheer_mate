"""
CheerMate - 陪伴机器人插件
一个温暖的陪伴插件，在你焦虑时无条件肯定你
"""
import asyncio
import json
import random
from typing import Set

from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from astrbot.core.utils.session_waiter import session_waiter, SessionController


@register(
    "CheerMate - 陪伴夸夸机器人",
    "warrior-dl",
    "一个温暖的陪伴插件，在你焦虑时无条件肯定你。每天晚上主动问候，通过AI回复提供情绪价值。",
    "0.2.2",
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

        # 定时任务 job_id 映射（user_id -> job_id）
        self.cron_job_ids: dict = {}

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
        
        # 使用 active_agent 方式为每个用户注册定时任务
        await self._register_cron_jobs()
        
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

    async def _register_cron_jobs(self):
        """为每个订阅用户注册 active_agent 定时任务"""
        try:
            cron_mgr = self.context.cron_manager
            if cron_mgr is None:
                logger.error(f"[CheerMate] CronJobManager 不可用，无法注册定时任务")
                return

            # 先清理旧的持久化任务
            await self._cleanup_old_cron_jobs()

            # 解析配置的时间为 cron 表达式
            hour, minute = map(int, self.scheduled_time.split(":"))
            cron_expression = f"{minute} {hour} * * *"  # 每天指定时间执行

            # 为每个订阅用户创建独立的 active_agent 任务
            for user_id in self.subscribers:
                payload = await self._build_payload(user_id)

                # 注册 active_agent 任务
                job = await cron_mgr.add_active_job(
                    name=f"CheerMate_Greeting_{user_id}",
                    cron_expression=cron_expression,
                    payload=payload,
                    description=f"每天 {self.scheduled_time} 向用户 {user_id} 发送个性化问候",
                    persistent=True,
                    enabled=True
                )

                # 保存 job_id（用于后续管理）
                self.cron_job_ids[user_id] = job.job_id
                logger.info(f"[CheerMate] 为用户 {user_id} 注册定时任务: job_id={job.job_id}")

            # 持久化 job_id 映射
            await self._save_cron_job_ids()
            logger.info(f"[CheerMate] 所有定时任务注册完成，共 {len(self.cron_job_ids)} 个")

        except Exception as e:
            logger.error(f"[CheerMate] 注册定时任务失败: {e}")

    async def _cleanup_old_cron_jobs(self):
        """清理上次运行遗留的定时任务"""
        try:
            old_job_ids = await self.get_kv_data("cron_job_ids", {})
            if not old_job_ids:
                return

            cron_mgr = self.context.cron_manager
            for user_id, job_id in old_job_ids.items():
                try:
                    await cron_mgr.delete_job(job_id)
                    logger.info(f"[CheerMate] 已清理旧任务: user={user_id}, job_id={job_id}")
                except Exception as e:
                    logger.warning(f"[CheerMate] 清理旧任务 {job_id} 失败（可能已不存在）: {e}")

            # 清空持久化数据
            await self.put_kv_data("cron_job_ids", {})
        except Exception as e:
            logger.error(f"[CheerMate] 清理旧定时任务失败: {e}")

    async def _save_cron_job_ids(self):
        """持久化 cron_job_ids 映射"""
        try:
            await self.put_kv_data("cron_job_ids", dict(self.cron_job_ids))
        except Exception as e:
            logger.error(f"[CheerMate] 保存 cron_job_ids 失败: {e}")

    def _build_greeting_note(self) -> str:
        """
        构建每日问候的任务指令（note）
        
        Returns:
            任务指令文本
        """
        try:
            return self.greeting_prompt.format(scheduled_time=self.scheduled_time)
        except KeyError as e:
            logger.warning(f"[CheerMate] greeting_prompt 包含未知占位符 {e}，已忽略")
            # 使用 format_map 忽略未知占位符
            class SafeDict(dict):
                def __missing__(self, key):
                    return "{" + key + "}"
            return self.greeting_prompt.format_map(
                SafeDict(scheduled_time=self.scheduled_time)
            )

    async def _build_payload(self, user_id: str) -> dict:
        """构建定时任务的 payload"""
        return {
            "session": user_id,
            "sender_id": "system",
            "note": self._build_greeting_note(),
            "origin": "plugin_cheermate"
        }

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

        # 为该用户创建定时任务
        try:
            cron_mgr = self.context.cron_manager
            if cron_mgr is None:
                yield event.plain_result("订阅失败：定时任务系统不可用")
                return

            hour, minute = map(int, self.scheduled_time.split(":"))
            cron_expression = f"{minute} {hour} * * *"

            payload = await self._build_payload(user_id)

            job = await cron_mgr.add_active_job(
                name=f"CheerMate_Greeting_{user_id}",
                cron_expression=cron_expression,
                payload=payload,
                description=f"每天 {self.scheduled_time} 向用户 {user_id} 发送个性化问候",
                persistent=True,
                enabled=True
            )

            self.cron_job_ids[user_id] = job.job_id
            await self._save_cron_job_ids()
            logger.info(f"[CheerMate] 用户 {user_id} 订阅成功，job_id={job.job_id}")

            reply = f"订阅成功！🌟\n\n每天 {self.scheduled_time}，我会主动问候你：\n\"今天感觉怎么样？有什么想分享的吗？\"\n\n如果不想收到推送，发送 /关闭陪伴 即可取消~"
            yield event.plain_result(reply)

        except Exception as e:
            logger.error(f"[CheerMate] 订阅失败: {e}")
            yield event.plain_result(f"订阅失败：{e}")

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

        # 删除该用户的定时任务
        try:
            cron_mgr = self.context.cron_manager
            if cron_mgr and user_id in self.cron_job_ids:
                job_id = self.cron_job_ids[user_id]
                await cron_mgr.delete_job(job_id)
                del self.cron_job_ids[user_id]
                await self._save_cron_job_ids()
                logger.info(f"[CheerMate] 用户 {user_id} 的定时任务已删除: job_id={job_id}")
        except Exception as e:
            logger.error(f"[CheerMate] 删除定时任务失败: {e}")

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

    @filter.command("reload_greeting", alias={"重载问候", "更新问候配置"})
    async def reload_greeting(self, event: AstrMessageEvent):
        """重新加载问候配置并更新定时任务（修改 greeting_prompt 后使用）"""
        user_id = event.unified_msg_origin

        if user_id not in self.subscribers:
            yield event.plain_result("你还没有订阅每日陪伴，无需重载配置~")
            return

        try:
            cron_mgr = self.context.cron_manager
            if cron_mgr is None:
                yield event.plain_result("重载失败：定时任务系统不可用")
                return

            # 删除旧任务
            if user_id in self.cron_job_ids:
                old_job_id = self.cron_job_ids[user_id]
                await cron_mgr.delete_job(old_job_id)
                logger.info(f"[CheerMate] 已删除旧任务: job_id={old_job_id}")

            # 创建新任务（使用最新的配置）
            hour, minute = map(int, self.scheduled_time.split(":"))
            cron_expression = f"{minute} {hour} * * *"

            payload = await self._build_payload(user_id)

            job = await cron_mgr.add_active_job(
                name=f"CheerMate_Greeting_{user_id}",
                cron_expression=cron_expression,
                payload=payload,
                description=f"每天 {self.scheduled_time} 向用户 {user_id} 发送个性化问候",
                persistent=True,
                enabled=True
            )

            self.cron_job_ids[user_id] = job.job_id
            await self._save_cron_job_ids()
            logger.info(f"[CheerMate] 已创建新任务: job_id={job.job_id}")

            reply = "问候配置已重载！✨\n下次定时问候将使用最新的 prompt 配置。"
            yield event.plain_result(reply)

        except Exception as e:
            logger.error(f"[CheerMate] 重载问候配置失败: {e}")
            yield event.plain_result(f"重载失败：{e}")

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
        
        # 删除所有定时任务
        try:
            cron_mgr = self.context.cron_manager
            if cron_mgr and self.cron_job_ids:
                for user_id, job_id in self.cron_job_ids.items():
                    try:
                        await cron_mgr.delete_job(job_id)
                        logger.info(f"[CheerMate] 已删除用户 {user_id} 的定时任务: job_id={job_id}")
                    except Exception as e:
                        logger.error(f"[CheerMate] 删除任务 {job_id} 失败: {e}")
            # 清空持久化的 job_ids
            await self.put_kv_data("cron_job_ids", {})
        except Exception as e:
            logger.error(f"[CheerMate] 删除定时任务时出错: {e}")
        
        logger.info(f"[CheerMate] 插件资源清理完成")
