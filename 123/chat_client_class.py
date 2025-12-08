#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chat_client_class.py
Client entry point: 构建 socket、状态机、GUI 并运行。
"""

import socket
import argparse
import sys
import threading

# 依赖：chat_utils.py 中应定义 SERVER, CHAT_PORT, mysend, myrecv
from chat_utils import SERVER, CHAT_PORT, mysend, myrecv
from client_state_machine import ClientSM
from GUI import GUI

# Chatbot 客户端抽象（可选）
try:
    from Chatbot_client import ChatBotClientOpenAI
except Exception:
    ChatBotClientOpenAI = None


class Client:
    def __init__(self, args):
        self.args = args
        self.socket = None
        self.sm = None
        self.gui = None
        self.proc_thread = None

        # 初始化 chatbot（若可用）
        self.chatbot = None
        if ChatBotClientOpenAI is not None:
            try:
                # 如果你想使用本地 host，可以在 args 中传入或修改这里
                self.chatbot = ChatBotClientOpenAI(name="TomAI")
            except Exception as e:
                print("Warning: ChatBotClientOpenAI init failed:", e)
                self.chatbot = None

    def quit(self):
        try:
            if self.socket:
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                self.socket.close()
        except Exception as e:
            print("Error while quitting:", e)
        finally:
            self.socket = None

    def init_chat(self):
        """建立 socket、状态机和 GUI（把 send/recv 注入 GUI）"""
        # create socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        svr = SERVER if self.args.d is None else (self.args.d, CHAT_PORT)
        try:
            self.socket.connect(svr)
        except Exception as e:
            print(f"Failed to connect to server {svr}: {e}")
            raise

        # create client state machine (handles JSON msg parsing/logic)
        self.sm = ClientSM(self.socket)

        # create GUI and inject send/recv and state machine
        # GUI will call send(msg) to send JSON text to server, and call recv() to read
        self.gui = GUI(self.send, self.recv, self.sm, self.socket, self.chatbot)

    def send(self, msg: str):
        """Wrapper around mysend for GUI to call."""
        if not self.socket:
            raise RuntimeError("Socket not initialized")
        try:
            mysend(self.socket, msg)
        except Exception as e:
            print("Send error:", e)
            raise

    def recv(self) -> str:
        """Wrapper around myrecv for GUI to call (returns raw string or empty)."""
        if not self.socket:
            return ""
        try:
            return myrecv(self.socket)
        except Exception as e:
            print("Recv error:", e)
            return ""

    def run_chat(self):
        """Start the GUI mainloop (blocking)."""
        try:
            self.init_chat()
        except Exception as e:
            print("Failed to initialize chat:", e)
            return

        try:
            # GUI.run() will start the login flow and mainloop
            self.gui.run()
        except KeyboardInterrupt:
            print("Interrupted by user.")
        except Exception as e:
            print("GUI runtime error:", e)
        finally:
            self.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat Client")
    parser.add_argument("-d", type=str, default=None, help="server IP addr (default from chat_utils.SERVER)")
    args = parser.parse_args()

    client = Client(args)
    client.run_chat()
