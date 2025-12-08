"""
chat_server.py
最终稳定版 —— 与 client_state_machine / GUI / server_actions 完全匹配
"""

import time
import socket
import select
import json
import sys
import pickle as pkl
from chat_utils import *
import chat_group as grp
from Chatbot_client import ChatBotClientOpenAI
from server_actions import (
    handle_connect,
    handle_exchange,
    handle_poem,
    handle_time,
    handle_list,
    handle_search,
    handle_add,
    handle_ai_query,
    handle_ai_private_chat,
    handle_disconnect,
    handle_summary,
    handle_keywords,
)


SERVER_PORT = 1111
MAX_MSG_SIZE = 1024


# ======================================================
# ChatServer 类
# ======================================================
class ChatServer:
    def __init__(self):
        self.logged_name2sock = {}     # username -> socket
        self.logged_sock2name = {}     # socket -> username

        self.new_clients = []          # 未登录的 socket
        self.all_sockets = []          # 所有 socket

        self.group = grp.Group()       # 管理群聊/私聊
        #self.sonnet = Sonnet()         # 用于 poem 功能

        # 搜索索引（每人一个）
        self.indices = {}

        # 群聊历史
        self.group_chat_history = {}   # key = sorted tuple(names)

        # AI 客户端
        self.ai = ChatBotClientOpenAI()

    # ======================================================
    # 启动服务器
    # ======================================================
    def start_server(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((socket.gethostname(), SERVER_PORT))
        print(f"[Server] Listening on port {SERVER_PORT}...")
        self.server.listen(5)

        self.all_sockets.append(self.server)

    # ======================================================
    # 新用户登录处理
    # ======================================================
    def new_client_login(self, clients_ready):
        for client in clients_ready:
            data = client.recv(MAX_MSG_SIZE).decode()
            if not data:
                # 客户端断开
                self.remove_client(client)
                continue

            try:
                msg = json.loads(data)
            except:
                continue

            if msg.get("action") != "login":
                continue

            name = msg.get("name")
            pwd_hash = msg.get("password")

            # 已登录
            if name in self.logged_name2sock:
                mysend(client, json.dumps({"status": "duplicate"}))
                continue

            # 检查密码（使用本地 user_data.pkl）
            try:
                with open("user_data.pkl", "rb") as f:
                    user_db = pkl.load(f)
            except:
                user_db = {}

            if name in user_db:
                # 用户存在 → 检查密码
                if user_db[name] != pwd_hash:
                    mysend(client, json.dumps({"status": "wrong-password"}))
                    continue
            else:
                # 新用户 → 注册
                user_db[name] = pwd_hash
                with open("user_data.pkl", "wb") as f:
                    pkl.dump(user_db, f)

            # 登录成功
            print(f"[Login] {name} logged in.")

            mysend(client, json.dumps({"status": "ok", "name": name}))

            # 加入登录用户
            self.new_clients.remove(client)
            self.logged_name2sock[name] = client
            self.logged_sock2name[client] = name

            # 创建对应的搜索索引器
            #self.indices[name] = Indexer()

    # ======================================================
    # 安全移除用户
    # ======================================================
    def remove_client(self, sock):
        if sock in self.new_clients:
            self.new_clients.remove(sock)
        if sock in self.all_sockets:
            self.all_sockets.remove(sock)

        if sock in self.logged_sock2name:
            name = self.logged_sock2name[sock]
            print(f"[Logout] {name} disconnected.")

            del self.logged_sock2name[sock]
            del self.logged_name2sock[name]

        try:
            sock.close()
        except:
            pass

    # ======================================================
    # 广播给聊天组内其他用户
    # ======================================================
    def broadcast_to_peers(self, from_name, msg):
        the_guys = self.group.list_me(from_name)
        for guy in the_guys:
            if guy == from_name:
                continue
            if guy in self.logged_name2sock:
                mysend(self.logged_name2sock[guy], msg)

    # ======================================================
    # 登录后的消息处理
    # ======================================================
    def logged_in_communication(self, clients_ready):
        for client in clients_ready:
            data = client.recv(MAX_MSG_SIZE).decode()
            if not data:
                self.remove_client(client)
                continue

            try:
                msg = json.loads(data)
            except:
                continue

            action = msg.get("action")
            from_name = self.logged_sock2name.get(client)

            if action == "connect":
                handle_connect(self, client, msg)

            elif action == "exchange":
                handle_exchange(self, client, msg)

            elif action == "poem":
                handle_poem(self, client, msg)

            elif action == "time":
                handle_time(self, client, msg)

            elif action == "list":
                handle_list(self, client, msg)

            elif action == "search":
                handle_search(self, client, msg)

            elif action == "add":
                handle_add(self, client, msg)

            elif action == "ai_query":
                handle_ai_query(self, client, msg)

            elif action == "ai_private_chat":
                handle_ai_private_chat(self, client, msg)

            elif action == "disconnect":
                handle_disconnect(self, client, msg)

            elif action == "summary":
                handle_summary(self, client, msg)

            elif action == "keywords":
                handle_keywords(self, client, msg)

            else:
                print(f"[Server] Unknown action: {action}")

    # ======================================================
    # 服务器主循环
    # ======================================================
    def run(self):
        self.start_server()

        while True:
            try:
                read, _, _ = select.select(self.all_sockets, [], [])
            except:
                continue

            for sock in read:
                if sock is self.server:
                    # 新连接
                    client, addr = self.server.accept()
                    print(f"[Connect] From {addr}")
                    self.new_clients.append(client)
                    self.all_sockets.append(client)
                else:
                    # 已有用户发来数据
                    if sock in self.new_clients:
                        self.new_client_login([sock])
                    else:
                        self.logged_in_communication([sock])


# ======================================================
# 主程序启动
# ======================================================
if __name__ == "__main__":
    server = ChatServer()
    server.run()
