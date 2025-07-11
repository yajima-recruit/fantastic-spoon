# launcher.py
from multiprocessing import Process, freeze_support
import time, sys

import server
import gui_app

def main():
    # サーバープロセスを起動
    p_server = Process(target=server.server_main, daemon=True)
    p_server.start()

    # 少し待って（サーバーが立ち上がる猶予）
    time.sleep(1)

    # GUIプロセスを起動（ブロッキング）
    p_gui = Process(target=gui_app.gui_main)
    p_gui.start()

    # GUI終了まで待機
    p_gui.join()

if __name__ == "__main__":
    freeze_support()
    main()
