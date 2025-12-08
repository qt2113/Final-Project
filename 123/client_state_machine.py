"""
client_state_machine.py
管理客户端的聊天逻辑，不处理 GUI，不处理 socket，只做“状态 + 命令解析”。
"""

from chat_utils import *
import json


class ClientSM:
    def __init__(self, s):
        self.state = S_OFFLINE
        self.peer = ''
        self.me = ''
        self.out_msg = ''
        self.s = s

    # 基本状态管理
    def set_state(self, state):
        self.state = state

    def get_state(self):
        return self.state

    def set_myname(self, name):
        self.me = name

    def get_myname(self):
        return self.me

    # ============================================================
    # 连接逻辑（单聊 / 群聊）
    # ============================================================
    def connect_to(self, peer):
        """支持单人私聊 & 群聊 ALL"""
        if peer.upper() == "ALL":
            msg = json.dumps({"action": "connect", "target": "ALL"})
            mysend(self.s, msg)
            self.peer = "ALL"
            self.out_msg += "You are now creating a group chat...\n"
            return True

        msg = json.dumps({"action": "connect", "target": peer})
        mysend(self.s, msg)
        response = json.loads(myrecv(self.s))

        if response["status"] == "success":
            self.peer = peer
            self.state = S_CHATTING
            self.out_msg += f'You are connected with {self.peer}\n'
            return True
        elif response["status"] == "busy":
            self.out_msg += "User is busy. Try later.\n"
        elif response["status"] == "self":
            self.out_msg += "Cannot talk to yourself.\n"
        else:
            self.out_msg += "User not online.\n"
        return False

    def disconnect(self):
        mysend(self.s, json.dumps({"action": "disconnect"}))
        self.out_msg += f"You are disconnected from {self.peer}\n"
        self.peer = ''

    # ============================================================
    # 状态机主逻辑
    # ============================================================
    def proc(self, my_msg, peer_msg):
        self.out_msg = ""

        # ============================================================
        # 1. 登录状态
        # ============================================================
        if self.state == S_LOGGEDIN:
            if len(my_msg) > 0:

                if my_msg == 'q':
                    self.out_msg += "See you next time!\n"
                    self.state = S_OFFLINE

                elif my_msg == 'time':
                    mysend(self.s, json.dumps({"action": "time"}))
                    time_in = json.loads(myrecv(self.s))["results"]
                    self.out_msg += "Time is: " + time_in

                elif my_msg == 'who':
                    mysend(self.s, json.dumps({"action": "list"}))
                    logged = json.loads(myrecv(self.s))["results"]
                    self.out_msg += "=== Online Users ===\n" + logged

                elif my_msg.startswith('@'):     # 请求聊天
                    peer = my_msg[1:].strip()
                    if self.connect_to(peer):
                        self.state = S_CHATTING
                        self.out_msg += f"Connect to {peer}. Chat away!\n\n"
                        self.out_msg += "-----------------------------------\n"
                    else:
                        self.out_msg += "Connection failed.\n"

                elif my_msg.startswith('?'):      # 搜索
                    term = my_msg[1:].strip()
                    mysend(self.s, json.dumps({"action": "search", "target": term}))
                    res = json.loads(myrecv(self.s))["results"]
                    self.out_msg += res if res else f"'{term}' not found\n"

                elif my_msg.startswith("p") and my_msg[1:].isdigit():  # 诗歌
                    idx = my_msg[1:].strip()
                    mysend(self.s, json.dumps({"action": "poem", "target": idx}))
                    poem = json.loads(myrecv(self.s))["results"]
                    self.out_msg += poem + '\n\n'

                else:
                    self.out_msg += menu

            # 处理来自服务器的连接请求
            if len(peer_msg) > 0:
                peer_msg = json.loads(peer_msg)
                if peer_msg["action"] == "connect":
                    self.peer = peer_msg["from"]
                    self.out_msg += f"Request from {self.peer}\nConnected.\n"
                    self.out_msg += "------------------------------------\n"
                    self.state = S_CHATTING

        # ============================================================
        # 2. 聊天中状态
        # ============================================================
        elif self.state == S_CHATTING:
            # 我发出的消息
            if len(my_msg) > 0:

                # AI 群聊问答
                if my_msg.startswith("@TomAI"):
                    query = my_msg[6:].strip()
                    if query:
                        mysend(self.s, json.dumps({
                            "action": "ai_query",
                            "query": query
                        }))
                        return self.out_msg

                # 添加成员
                if my_msg.startswith("add "):
                    new_user = my_msg[4:].strip()
                    mysend(self.s, json.dumps({"action": "add", "target": new_user}))
                    return self.out_msg

                # 摘要
                if my_msg == "/summary":
                    mysend(self.s, json.dumps({"action": "summary"}))
                    self.out_msg += "Generating summary...\n"
                    return self.out_msg

                # 关键词
                if my_msg == "/keywords":
                    mysend(self.s, json.dumps({"action": "keywords"}))
                    self.out_msg += "Extracting keywords...\n"
                    return self.out_msg

                # 离开聊天
                if my_msg == 'bye':
                    mysend(self.s, json.dumps({
                        "action": "exchange",
                        "from": f"[{self.me}]",
                        "message": "bye"
                    }))
                    return self.out_msg

                # 普通聊天
                mysend(self.s, json.dumps({
                    "action": "exchange",
                    "from": f"[{self.me}]",
                    "message": my_msg
                }))
                self.out_msg += f"[{self.me}]: {my_msg}\n"
                return self.out_msg

            # --- 对方发来的消息 ---
            if len(peer_msg) > 0:
                peer_msg = json.loads(peer_msg)

                # 有人加入
                if peer_msg["action"] == "connect" and peer_msg.get("status") == "request":
                    self.out_msg += f"({peer_msg['from']} joined the chat)\n"

                # 普通聊天消息（群聊 or 单聊）
                elif peer_msg["action"] == "exchange":
                    sender = peer_msg["from"]
                    content = peer_msg["message"]
                    sentiment = peer_msg.get("sentiment", "neutral")

                    # 表情
                    if sender != "[TomAI]":
                        emoji = "😊" if sentiment == "positive" else \
                                "😢" if sentiment == "negative" else "😐"
                        self.out_msg += f"{sender}{content} {emoji}\n"
                    else:
                        self.out_msg += f"{sender}{content}\n"

                # 群聊历史
                elif peer_msg["action"] == "history":
                    history = peer_msg.get("results", [])
                    self.out_msg += "\n===== Chat History =====\n"
                    for r in history:
                        t = r.get("timestamp")
                        s = r.get("from")
                        c = r.get("message")
                        self.out_msg += f"{t} {s}: {c}\n"
                    self.out_msg += "===== End =====\n\n"

                # 断开
                elif peer_msg["action"] == "disconnect":
                    self.out_msg += f"{self.peer} left the chat.\n"
                    self.state = S_LOGGEDIN
                    self.peer = ''

                # AI 私聊结果（GUI 会再次处理）
                elif peer_msg["action"] == "ai_private_chat_result":
                    self.out_msg += f"[TomAI 私聊]: {peer_msg['results']}\n"

                # 摘要结果
                elif peer_msg["action"] == "summary_result":
                    r = peer_msg.get("results", "失败")
                    self.out_msg += f"📋 Summary:\n{r}\n\n"

                # 关键词
                elif peer_msg["action"] == "keywords_result":
                    r = peer_msg.get("results", "失败")
                    self.out_msg += f"📌 Keywords:\n{r}\n\n"

        else:
            self.out_msg += "Invalid state.\n"
            print_state(self.state)

        return self.out_msg
