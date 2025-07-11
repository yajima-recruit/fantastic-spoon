# comment_fetcher.py
import asyncio
import websockets
import pytchat
import json
from typing import Optional


class YouTubeCommentFetcher:
    def __init__(self, video_id):
        self.chat = pytchat.create(video_id=video_id)

    async def fetch(self, message_callback):
        while self.chat.is_alive():
            for item in self.chat.get().sync_items():  # type: ignore
                await message_callback(
                    {
                        "command": False,
                        "name": item.author.name, 
                        "message": item.message
                    }
                )
            await asyncio.sleep(0.5)


class TwitchCommentFetcher:
    def __init__(self, channel, nickname, token):
        self.server = "irc.chat.twitch.tv"
        self.port = 6667
        self.channel = f"#{channel.lower()}"
        self.nickname = nickname
        self.token = token
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.server, self.port)
        self.send_line(f"PASS {self.token}")
        self.send_line(f"NICK {self.nickname}")

        # ここを追加 → タグ情報（display-nameなど）を取得するためのリクエスト
        self.send_line("CAP REQ :twitch.tv/tags")

        self.send_line(f"JOIN {self.channel}")

    def send_line(self, line):
        if self.writer:
            self.writer.write((line + "\r\n").encode("utf-8"))

    async def fetch(self, message_callback):
        await self.connect()
        while True:
            line = await self.reader.readline()  # type: ignore
            if not line:
                break
            line = line.decode("utf-8").strip()
            if line.startswith("PING"):
                self.send_line("PONG :tmi.twitch.tv")
                await self.writer.drain()  # type: ignore
                continue

            if "PRIVMSG" in line:
                try:
                    tags = {}
                    if line.startswith("@"):
                        raw_tags, line = line.split(" ", 1)
                        for tag in raw_tags[1:].split(";"):
                            if "=" in tag:
                                k, v = tag.split("=", 1)
                                tags[k] = v

                    # fallback: IDから名前を取得
                    username = tags.get("display-name") or line.split("!", 1)[0][1:]

                    message = line.split("PRIVMSG", 1)[1].split(":", 1)[1]

                    await message_callback(
                        {
                            "command": False,
                            "name": username,
                            "message": message
                        }
                    )
                except Exception as e:
                    print("パースエラー:", e)


class WebSocketSender:
    def __init__(self, uri):
        self.uri = uri
        self.websocket = None

    async def connect(self):
        self.websocket = await websockets.connect(self.uri)

    async def send(self, data):
        if self.websocket is not None:
            await self.websocket.send(json.dumps(data))

    async def close(self):
        if self.websocket:
            await self.websocket.close()
