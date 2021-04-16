# 파트너 봇 "한마루" 와의 데이터 공유를 위한 모듈입니다.

import pickle
import os

import discord
from discord.ext import commands
# from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ext.db import read, config, db


class Handler:
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot
        self._input = 781893295415885834
        self._output = 781893272640421949
        self.export_path = "general/hanmaru_export.bin"
        self.fetch_path = "general/hanmaru_fetched.bin"
        self.queue = dict()
        # self.scheduler = AsyncIOScheduler()
        # self.scheduler.add_job(self.send, 'interval', seconds=10)
        # self.scheduler.start()

    async def send(self):
        if not self.queue:
            return
        with open(self.export_path, 'wb') as f:
            pickle.dump(self.queue, f)
        await self.bot.get_channel(self._output).send(f"업데이트: {len(self.queue)} 명", file=discord.File(self.export_path, filename="export"))
        os.remove(self.export_path)
        self.queue = dict()

    async def get(self, ctx: commands.Context):
        if ctx.channel.id == self._input and ctx.author.id == (699565735076167700 if config('test') else 686460052982464522) and ctx.message.attachments:
            if ctx.message.attachments[0].filename == 'export':
                await ctx.message.attachments[0].save(self.fetch_path)
                with open(self.fetch_path, 'rb') as f:
                    new_input = pickle.load(f)
                for k, v in new_input.items():
                    db.hanmaru.update_one({'_id': int(k)}, v, {'upsert': True})
                os.remove(self.fetch_path)

    def add_queue(self, user: int):
        self.queue[user] = read(user)
