# gui_app.py
import customtkinter as ctk
import asyncio
import threading
from comment_fetcher import TwitchCommentFetcher, YouTubeCommentFetcher, WebSocketSender
import configparser
from urllib.parse import urlparse, parse_qs
import sys
import os

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("コメント監視ツール")
        self.geometry("400x300")
        self.minsize(400, 300)

        # ====== 外枠フレーム（中央揃え＆上下余白）======
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", pady=20, padx=20)

        # ====== URLエリア ======
        frame_url = ctk.CTkFrame(main_frame)
        frame_url.pack(fill="x", pady=10)

        label_url = ctk.CTkLabel(frame_url, text="URL")
        label_url.grid(row=0, column=0, padx=5, pady=5)

        self.entry_url = ctk.CTkEntry(frame_url)
        self.entry_url.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        start_button = ctk.CTkButton(frame_url, text="コメント取得開始", command=self.start_comment)
        start_button.grid(row=1, column=1, padx=5, pady=5)

        frame_url.grid_columnconfigure(0, weight=1)

        # ====== キーワードエリア ======
        frame_join_exit = ctk.CTkFrame(main_frame)
        frame_join_exit.pack(fill="x", pady=10)

        label_join = ctk.CTkLabel(frame_join_exit, text="参加キーワード")
        label_join.grid(row=0, column=0, padx=5, pady=5)

        label_exit = ctk.CTkLabel(frame_join_exit, text="辞退キーワード")
        label_exit.grid(row=0, column=1, padx=5, pady=5)

        self.entry_join = ctk.CTkEntry(frame_join_exit)
        self.entry_join.insert(0, "参加希望")
        self.entry_join.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.entry_exit = ctk.CTkEntry(frame_join_exit)
        self.entry_exit.insert(0, "辞退")
        self.entry_exit.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        adapt_button = ctk.CTkButton(frame_join_exit, text="キーワード適応", command=self.send_keyword)
        adapt_button.grid(row=1, column=2, padx=5, pady=5)

        frame_join_exit.grid_columnconfigure(0, weight=1)
        frame_join_exit.grid_columnconfigure(1, weight=1)

        # ====== 繰り上げエリア ======
        frame_move_up = ctk.CTkFrame(main_frame)
        frame_move_up.pack(pady=10)

        label_move_up1 = ctk.CTkLabel(frame_move_up, text="待機列から")
        label_move_up1.pack(side="left", padx=5, pady=5)

        self.entry_move_up = ctk.CTkEntry(frame_move_up, width=30, justify="center")
        self.entry_move_up.insert(0, "3")
        self.entry_move_up.pack(side="left", padx=5, pady=5)

        label_move_up2 = ctk.CTkLabel(frame_move_up, text="人")
        label_move_up2.pack(side="left", padx=5, pady=5)

        move_up_button = ctk.CTkButton(frame_move_up, text="プレイ中に移動させる", command=self.send_move_up)
        move_up_button.pack(side="left", padx=5, pady=5)

        # 非同期ループとWebSocket
        self.ws_sender = WebSocketSender("ws://localhost:8000/ws?key=A")
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        # サーバーと接続をする
        asyncio.run_coroutine_threadsafe(self.ws_sender.connect(), self.loop)

    def send_keyword(self):
        # 参加キーワードを送る
        join_kw = self.entry_join.get()
        asyncio.run_coroutine_threadsafe(self.ws_sender.send(
            {
                "command": True,
                "name": "join_command",
                "message": join_kw
            }
        ), self.loop)

        # 辞退キーワードを送る
        exit_kw = self.entry_exit.get()
        asyncio.run_coroutine_threadsafe(self.ws_sender.send(
            {
                "command": True,
                "name": "exit_command",
                "message": exit_kw
            }
        ), self.loop)

    def start_comment(self):
        # 参加辞退コメントを先にセット
        self.send_keyword()

        # urlを取得
        url = self.entry_url.get()

        # urlがyoutube
        if "youtube" in url:
            #urlからビデオidを取り出す
            video_id = extract_video_id(url)

            # ビデオidがNoneじゃない場合
            if video_id is not None:
                # ビデオidでコメント取得起動
                asyncio.run_coroutine_threadsafe(self.start_youtube(video_id), self.loop)
            else:
                print("Noneです")

        # urlがtwitch
        elif "twitch" in url:
            # urlからユーザー名を取り出す
            username = extract_twitch_username(url)

            # ユーザー名がNoneじゃない場合
            if username is not None:
                # ユーザー名でコメント取得起動
                asyncio.run_coroutine_threadsafe(self.start_twitch(username), self.loop)
            else:
                print("Noneです")

    def send_move_up(self):
        # プレイ中にする人数を送る
        people_count = self.entry_move_up.get()
        asyncio.run_coroutine_threadsafe(self.ws_sender.send(
            {
                "command": True,
                "name": "move_up",
                "message": people_count
            }
        ), self.loop)

    async def start_twitch(self, channel):
        config = configparser.ConfigParser()
        config.read(exe_dir + "config.ini")
        fetcher = TwitchCommentFetcher(
            channel=channel,
            nickname=config["Twitch"]["BOT_NICK"],
            token=f'oauth:{config["Twitch"]["OAUTH_TOKEN"]}'
        )
        await fetcher.fetch(self.ws_sender.send)

    async def start_youtube(self, video_id):
        if not video_id:
            print("YouTubeの動画IDを入力してください")
            return
        fetcher = YouTubeCommentFetcher(video_id)
        await fetcher.fetch(self.ws_sender.send)

def extract_video_id(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return query.get("v", [None])[0]

def extract_twitch_username(url):
    parsed = urlparse(url)
    path = parsed.path.lstrip('/')  # 先頭の / を削除
    return path or None

if getattr(sys, 'frozen', False):
    # PyInstallerでビルドされた実行ファイルの場合
    exe_dir = os.path.dirname(sys.executable) + '\\'
else:
    # 通常のPythonスクリプトとして実行されている場合
    exe_dir = os.path.dirname(os.path.abspath(__file__)) + '\\'

def gui_main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    app = App()
    app.mainloop()
