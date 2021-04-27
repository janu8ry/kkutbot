import os
import pickle

import discord
from discord.ext import commands

from ext.db import config, read

# from apscheduler.schedulers.asyncio import AsyncIOScheduler



class Handler:
    """File transfer handler for partner bot 'hanmaru'"""

    __slots__ = ("bot", "_input", "_output", "export_path", "fetch_path", "queue")

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
        """sends data file to output channel"""
        if not self.queue:
            return
        with open(self.export_path, 'wb') as f:
            pickle.dump(self.queue, f)
        await self.bot.get_channel(self._output).send(f"업데이트: {len(self.queue)} 명", file=discord.File(self.export_path, filename="export"))
        os.remove(self.export_path)
        self.queue = dict()

    async def get(self, ctx: commands.Context):
        """fetches data file from input channel"""
        if ctx.channel.id == self._input and ctx.author.id == (699565735076167700 if config('test') else 686460052982464522) and ctx.message.attachments:
            if ctx.message.attachments[0].filename == 'export':
                await ctx.message.attachments[0].save(self.fetch_path)
                with open(self.fetch_path, 'rb') as f:
                    new_input = pickle.load(f)
                for k, v in new_input.items():
                    self.bot.db.hanmaru.update_one({'_id': int(k)}, v, {'upsert': True})  # noqa
                os.remove(self.fetch_path)

    def add_queue(self, user: int):  # adds changed user data to queue
        self.queue[user] = read(user)
