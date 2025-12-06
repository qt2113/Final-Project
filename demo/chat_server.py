"""
Created on Tue Jul 22 00:47:05 2014

@author: alina, zzhang
"""

import time
import socket
import select
import sys
import string
import indexer
import json
import pickle as pkl
from chat_utils import *
import chat_group as grp
from Chatbot_client import ChatBotClientOpenAI
from server_actions import (
    handle_connect, handle_exchange, handle_ai_query,
    handle_disconnect, handle_time, handle_list, handle_search, handle_add
)

class AI:
    def __init__(self):
        from Chatbot_client import ChatBotClientOpenAI
        self.llm = ChatBotClientOpenAI()
    
    def get_sentiment(self, text):
        """
        使用 LLM 分析情绪，返回 'positive', 'negative', 'neutral'
        """
        prompt = f"请判断这段话的情绪: {text}。只返回 positive/negative/neutral。"
        try:
            resp = self.llm.chat(prompt)
            resp = resp.lower()
            if 'positive' in resp:
                return 'positive'
            elif 'negative' in resp:
                return 'negative'
            else:
                return 'neutral'
        except Exception as e:
            print("AI情绪分析失败:", e)
            return 'neutral'

class Server:
    def __init__(self):
        self.new_clients = [] #list of new sockets of which the user id is not known
        self.logged_name2sock = {} #dictionary mapping username to socket
        self.logged_sock2name = {} # dict mapping socket to user name
        self.all_sockets = []
        self.group = grp.Group()
        #start server
        self.server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(SERVER)
        self.server.listen(5)
        self.all_sockets.append(self.server)
        #initialize past chat indices
        self.indices={}
        self.chat_history = {} 
        self.ai = AI()  # 用于存放用户发送的聊天消息及情绪
        self.group_chat_history = {}  # 记录每个群的聊天历史
        self.chat_memory = {}
                
        self.ACTION_MAP = {
            "connect": handle_connect,
            "exchange": handle_exchange,
            "ai_query": handle_ai_query,
            "disconnect": handle_disconnect,
            "time": handle_time,
            "list": handle_list,
            "search": handle_search,
            "add": handle_add,
            }


        # sonnet
        # self.sonnet_f = open('AllSonnets.txt.idx', 'rb')
        # self.sonnet = pkl.load(self.sonnet_f)
        # self.sonnet_f.close()
        #self.sonnet = indexer.PIndex("AllSonnets.txt")
        self.tom_ai = ChatBotClientOpenAI()   
        self.ai_name = "TomAI"
        self.logged_name2sock[self.ai_name] = None       
        self.logged_sock2name[None] = self.ai_name      
        print("TomAI has joined the chat system.")

    def call_remote_ai(self, query):
            try:
                return self.tom_ai.chat(query)
            except Exception as e:
                return f"TomAI 暂时开小差了～ {e}"
            
    def new_client(self, sock):
        #add to all sockets and to new clients
        print('new client...')
        sock.setblocking(0)
        self.new_clients.append(sock)
        self.all_sockets.append(sock)

    def login(self, sock):
        try:
            raw = myrecv(sock)
            if not raw:
                return
            msg = json.loads(raw)

            if msg.get("action") != "login":
                return

            name = msg["name"].strip()
            password_received = msg.get("password", "")  # 明文密码

            # 防止重复登录
            if self.group.is_member(name):
                mysend(sock, json.dumps({"action": "login", "status": "duplicate"}))
                return

            if sock in self.new_clients:
                self.new_clients.remove(sock)

            self.logged_name2sock[name] = sock
            self.logged_sock2name[sock] = name

            # 加载或创建用户索引
            if name not in self.indices:
                try:
                    self.indices[name] = pkl.load(open(f"{name}.idx", "rb"))
                except (IOError, EOFError, pkl.UnpicklingError):
                    self.indices[name] = indexer.Index(name)

            user_idx = self.indices[name]

            # === 密码处理逻辑 ===
            password_hash = getattr(user_idx, "password_hash", None)

            if password_hash:
                # 老用户或已有密码：必须匹配
                if not user_idx.check_password(password_received):
                    del self.logged_name2sock[name]
                    del self.logged_sock2name[sock]
                    mysend(sock, json.dumps({"action": "login", "status": "wrong-password"}))
                    return
            else:
                # 新用户或老用户第一次登录：设置密码
                user_idx.set_password(password_received)

            # 登录成功
            print(f"{name} logged in")
            self.group.join(name)
            mysend(sock, json.dumps({"action": "login", "status": "ok", "name": name}))

        except Exception as e:
            print("login exception:", e)

    

    def logout(self, sock):
        #remove sock from all lists
        name = self.logged_sock2name[sock]
        pkl.dump(self.indices[name], open(name + '.idx','wb'))
        del self.indices[name]
        del self.logged_name2sock[name]
        del self.logged_sock2name[sock]
        self.all_sockets.remove(sock)
        self.group.leave(name)
        sock.close()

#==============================================================================
# main command switchboard
#==============================================================================
    def handle_msg(self, from_sock):
        msg = myrecv(from_sock)
        if not msg:
            self.logout(from_sock)
            return
        msg = json.loads(msg)
        if msg.get("action") == "login":
            # 已经登录的 socket 不可能再发 login，直接忽略（防止误报）
            return
        action = msg.get("action")
        handler = self.ACTION_MAP.get(action)
        if handler:
            handler(self, from_sock, msg)   # 直接调用
        else:
            print("未知 action:", action)

    def broadcast_to_peers(self, sender_name, msg_json_str):
        _, gkey = self.group.find_group(sender_name)
        if gkey not in self.group.chat_grps:
            return
        for name in self.group.chat_grps[gkey]:
            if name == "TomAI":      # 只跳过机器人
                continue
            sock = self.logged_name2sock.get(name)
            if sock:
                mysend(sock, msg_json_str)   # 包括 sender 自己！

#==============================================================================
# main loop, loops *forever*
#==============================================================================
    def run(self):
        print ('starting server...')
        while(1):
           read,write,error=select.select(self.all_sockets,[],[])
           print('checking logged clients..')
           for logc in list(self.logged_name2sock.values()):
               if logc in read:
                   self.handle_msg(logc)
           print('checking new clients..')
           for newc in self.new_clients[:]:
               if newc in read:
                   self.login(newc)
           print('checking for new connections..')
           if self.server in read :
               #new client request
               sock, address=self.server.accept()
               self.new_client(sock)





def main():
    server=Server()
    server.run()

main()
