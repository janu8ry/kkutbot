"""
original code made by https://github.com/eunwoo1104
repo: https://github.com/eunwoo1104/light-koreanbots
"""

import asyncio
import logging

import aiohttp
from discord.ext import commands

logger = logging.getLogger("kkutbot")


class Client:
    """
    Koreanbots.dev, top.gg client for post guild count & get heart info

    Attributes
    ==========
    bot: commands.AutoShardedBot
        bot object to get guild count
    koreanbots_token: str
        koreanbots.dev token for REST api
    topgg_token: str
        top.gg token for REST api
    post: bool
        whether to automaticly post server count to two websites
    """

    def __init__(
        self,
        bot: commands.AutoShardedBot,
        koreanbots_token: str,
        topgg_token: str,
        post: bool = True,
    ):
        self.bot = bot
        self.koreanbots_token = koreanbots_token
        self.topgg_token = topgg_token
        self.loop = asyncio.get_event_loop()
        self.before = 0
        self.BASEURL = {
            "koreanbots": "https://api.koreanbots.dev/v2/bots",
            "topgg": "https://top.gg/api/bots/",
        }
        if post:
            self.loop.create_task(self.update_all())

    async def koreanbots_update(self):
        """
        post guild count to koreanbots.dev
        """
        if self.before == len(self.bot.guilds):
            return

        headers = {"Authorization": self.koreanbots_token}

        body = {"servers": len(self.bot.guilds)}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASEURL['koreanbots']}/{self.bot.user.id}/stats",
                headers=headers,
                json=body,
            ) as raw_resp:
                resp = await raw_resp.json()
                if resp["code"] == 200:
                    self.before = len(self.bot.guilds)
                    logger.info("한국 디스코드봇 리스트에 성공적으로 서버수를 업데이트 했습니다.")
                elif resp["code"] == 429:
                    logger.debug("한국 디스코드봇 리스트 서버수 업데이트 건너뜀. (레이트리밋)")
                else:
                    logger.error(
                        f"한국 디스코드봇 리스트 서버수 업데이트에 실패했습니다. 에러 코드: {resp['code']}, 내용: {resp['message']}"
                    )

    async def topgg_update(self):
        """
        post guild count to top.gg
        """
        if self.before == len(self.bot.guilds):
            return

        headers = {"Authorization": self.topgg_token}

        body = {
            "server_count": len(self.bot.guilds),
            "shard_count": self.bot.shard_count,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASEURL['topgg']}/{self.bot.user.id}/stats",
                headers=headers,
                json=body,
            ) as raw_resp:
                resp = await raw_resp.json()
                if resp["code"] == 200:
                    self.before = len(self.bot.guilds)
                    logger.info("top.gg에 성공적으로 서버수를 업데이트 했습니다.")
                elif resp["code"] == 429:
                    logger.debug("top.gg 서버수 업데이트 건너뜀. (레이트리밋)")
                else:
                    logger.error(
                        f"top.gg 서버수 업데이트에 실패했습니다. 에러 코드: {resp['code']}, 내용: {resp['message']}"
                    )

    async def update_all(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            await self.koreanbots_update()
            await self.topgg_update()
            await asyncio.sleep(60)
