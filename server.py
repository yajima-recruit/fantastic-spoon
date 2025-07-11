from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import json
from typing import Set, List

# 参加者クラス
class Participant:
    """
    参加者を表すクラス。

    Attributes:
        username (str): ユーザー名。
        participation_count (int): 参加回数。
    """
    __slots__ = ("username", "participation_count")
    def __init__(self, username):
        self.username = username
        self.participation_count = 0

    def equalName(self, name):
        return self.username == name

def existsParticipantList(name):
    """
    参加者名簿に存在するかどうか確認する関数。\n
    存在すればインスタンスを返し、\n
    存在しなければNoneを返す。

    Args:
        name (str): 調べたい参加者の名前。
    """
    for instance in participant_list:
        if instance.equalName(name):
            return instance
    return None

def existsWaitingQueue(name):
    """
    待機列に存在するかどうか確認する関数。\n
    存在すればインスタンスを返し、\n
    存在しなければNoneを返す。

    Args:
        name (str): 調べたい参加者の名前。
    """
    instance = existsParticipantList(name)
    if instance is not None:
        # そのインスタンスが待機列に存在するか
        if instance in waiting_queue:
            return instance
        else:
            return None
    else:
        return None

async def broadcastWaitingQueue():
    """
    待機列の最新状態を connections["C"] に送信する関数。
    """
    # 待機列を並び替える
    waiting_queue.sort(key=lambda p: p.participation_count)

    data = {
        "queue": [p.username for p in waiting_queue]
    }

    message = json.dumps(data)

    for c_ws in connections["C"]:
        try:
            await c_ws.send_text(message)
        except Exception:
            # 接続が切れている場合などを想定
            pass

async def broadcastPlayingList():
    """
    待機列の最新状態を connections["D"] に送信する関数。
    """
    data = {
        "list": [p.username for p in playing_list]
    }

    message = json.dumps(data)

    for d_ws in connections["D"]:
        try:
            await d_ws.send_text(message)
        except Exception:
            # 接続が切れている場合などを想定
            pass

# 変数定義
join_word = ""
exit_word = ""
participant_list: Set[Participant] = set()
waiting_queue: List[Participant] = []
playing_list: List[Participant] = []

app = FastAPI()

# Aは単一接続、Bは複数接続を格納するリスト
connections = {
    "A": None,
    "B": [],
    "C": [],
    "D": [],
}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, key: str):
    global join_word, exit_word, waiting_queue
    await websocket.accept()

    if key not in connections:
        await websocket.close(code=1008)
        return

    if key == "A":
        # Aは重複禁止なので既存接続あれば切断して上書き
        if connections["A"]:
            await connections["A"].close()
        connections["A"] = websocket

    else:
        # B, C, Dは重複許可なので追加
        connections[key].append(websocket)

    try:
        if key == "A":
            while True:
                msg = await websocket.receive_text()
                
                try:
                    data = json.loads(msg)  # ← JSON文字列を辞書に変換！
                    command = data.get("command")
                    name = data.get("name")
                    message = data.get("message")
                    print(f"コマンド:{command}; 名前:{name}; メッセージ:{message}")
                    
                    # コマンドかどうか
                    if command:
                        # どのコマンドか
                        # 参加コメント
                        if name == "join_command":
                            join_word = message
                        # 辞退コメント
                        elif name == "exit_command":
                            exit_word = message
                        # 待機列からプレイ中に移動
                        elif name == "move_up":
                            # 移動人数
                            people_count = int(message)
                            # プレイイングリストを空にする
                            playing_list.clear()

                            # 人数を移動させる
                            subset = waiting_queue[:people_count]
                            # waiting_queue からも消す
                            del waiting_queue[:people_count]

                            # 取り出された人の参加回数を増やす
                            for people in subset:
                                people.participation_count += 1
                            playing_list.extend(subset)

                            # Cに待機列情報を送る
                            await broadcastWaitingQueue()
                            # Dにプレイ中情報を送る
                            await broadcastPlayingList()

                    # 空メッセージだった場合スキップ
                    elif message.strip() != "":
                        # Bの全接続に転送（必要ならdataをそのまま送る）
                        # Bの全接続にメッセージを送信
                        for b_ws in connections["B"]:
                            try:
                                await b_ws.send_text(json.dumps(
                                    {
                                        "username": name,
                                        "message": message
                                    }
                                ))
                            except Exception:
                                # 送信失敗なら切断済みの可能性。後処理で削除します
                                pass
                        
                        # コメントが参加だった場合
                        if join_word in message:
                            print(f"{name} : 参加待機")
                            # 参加者名簿に名前が存在するかどうか確認する
                            instance = existsParticipantList(name)
                            # インスタンスが存在しない場合、参加者名簿に追加
                            if instance is None:
                                instance = Participant(name)
                                participant_list.add(instance)
                            # 待機列とプレイイングリストにインスタンスが存在しない場合、待機列に追加
                            if instance not in waiting_queue and instance not in playing_list:
                                waiting_queue.append(instance)

                            # Cに待機列情報を送る
                            await broadcastWaitingQueue()

                        # コメントが辞退だった場合     
                        elif exit_word in message:
                            print(f"{name} : 辞退")
                            # 待機列にインスタンスが存在するか
                            instance = existsWaitingQueue(name)
                            if instance is not None:
                                waiting_queue = [p for p in waiting_queue if p != instance]
                            
                            # Cに待機列情報を送る
                            await broadcastWaitingQueue()

                except json.JSONDecodeError:
                    # JSONデコード失敗
                    pass
        else:
            # B, Cは受信なし（接続維持のみ）
            while True:
                await websocket.receive_text()

    except WebSocketDisconnect:
        print(f"{key}の接続が切れました")
    finally:
        # 接続解除時に接続リストから削除
        if key == "A":
            connections["A"] = None
        else:
            if websocket in connections["B"]:
                connections["B"].remove(websocket)

def server_main():
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None,   # ← ここがキモ
        access_log=False
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
