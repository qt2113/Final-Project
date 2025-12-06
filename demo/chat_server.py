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
import re

def remove_emoji(text):
    # 匹配大部分emoji字符
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # 表情符号
        "\U0001F300-\U0001F5FF"  # 符号 &  pictographs
        "\U0001F680-\U0001F6FF"  # 交通工具 & 符号
        "\U0001F1E0-\U0001F1FF"  # 国旗
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)


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
            msg = json.loads(raw)

            if len(msg) > 0:

                if msg["action"] == "login":
                    name = msg["name"]
                    password = msg.get("password", "")

                    # ====== 新增：如果重复登录 ======
                    if self.group.is_member(name):
                        mysend(sock, json.dumps({
                            "action": "login",
                            "status": "duplicate"
                        }))
                        print(name + " duplicate login attempt")
                        return

                    # ====== 原逻辑：移动 socket ======
                    if sock in self.new_clients:
                        self.new_clients.remove(sock)

                    self.logged_name2sock[name] = sock
                    self.logged_sock2name[sock] = name

                    # ====== 原逻辑：第一次加载 index ======
                    if name not in self.indices.keys():
                        try:
                            # 尝试读取本地 index
                            self.indices[name] = pkl.load(open(name + '.idx', 'rb'))

                            # ====== 新增：检查密码 ======
                            if getattr(self.indices[name], "password", None) != password:
                                mysend(sock, json.dumps({
                                    "action": "login",
                                    "status": "wrong-password"
                                }))
                                return

                            # 密码正确 → 登录成功
                            print(name + " logged in")
                            self.group.join(name)
                            mysend(sock, json.dumps({
                                "action": "login",
                                "status": "ok",
                                "name": name
                            }))
                            return

                        except IOError:
                            # index不存在 → 第一次登录
                            self.indices[name] = indexer.Index(name)
                            # ====== 新增：保存密码到 index ======
                            self.indices[name].password = password

                            print(name + " logged in (first time)")
                            self.group.join(name)
                            mysend(sock, json.dumps({
                                "action": "login",
                                "status": "ok",
                                "name": name
                            }))
                            return

                    else:
                        # 第二次登录（index已经在内存中）
                        idx = self.indices[name]

                        # ====== 新增密码检查 ======
                        if getattr(idx, "password", None) != password:
                            mysend(sock, json.dumps({
                                "action": "login",
                                "status": "wrong-password"
                            }))
                            return

                        print(name + " logged in")
                        self.group.join(name)
                        mysend(sock, json.dumps({
                            "action": "login",
                            "status": "ok",
                            "name": name
                        }))
                        return

                else:
                    print("wrong code received")

            else:
                self.logout(sock)

        except Exception as e:
            print("login exception:", e)
            if sock in self.all_sockets:
                self.all_sockets.remove(sock)

    

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
        #read msg code
        msg = myrecv(from_sock)
        if len(msg) > 0:
#==============================================================================
# handle connect request
#==============================================================================
            msg = json.loads(msg)
            if msg["action"] == "connect":
                to_name = msg["target"]
                from_name = self.logged_sock2name[from_sock]
                # ===== 群聊：connect ALL =====
                if to_name == "ALL":
                    print("Group chat requested by", from_name)
                    self.group.connect_all()

                    # 给所有人广播：群聊创建
                    for user, sock in self.logged_name2sock.items():
                        mysend(sock, json.dumps({
                            "action": "connect",
                            "status": "group-created",
                            "from": from_name
                        }))

                    # 给请求者返回成功
                    mysend(from_sock, json.dumps({
                        "action": "connect",
                        "status": "success"
                    }))
                    return
                # ===== 个人私聊 =====
                if to_name == from_name:
                    msg = json.dumps({"action":"connect", "status":"self"})
                # connect to the peer
                elif self.group.is_member(to_name):
                    to_sock = self.logged_name2sock[to_name]
                    self.group.connect(from_name, to_name)
                    the_guys = self.group.list_me(from_name)
                    msg = json.dumps({"action":"connect", "status":"success"})
                    for g in the_guys[1:]:
                        to_sock = self.logged_name2sock[g]
                        mysend(to_sock, json.dumps({"action":"connect", "status":"request", "from":from_name}))
                else:
                    msg = json.dumps({"action":"connect", "status":"no-user"})
                mysend(from_sock, msg)
#==============================================================================
# handle messeage exchange: one peer for now. will need multicast later
#==============================================================================
            elif msg["action"] == "exchange":
                from_name = self.logged_sock2name[from_sock]
                the_guys = self.group.list_me(from_name)
                said = msg["from"]+msg["message"]
                #===================== 新增：AI情绪分析 =====================
                if from_name != "TomAI":                # 新增判断
                    sentiment = self.ai.get_sentiment(msg["message"])
                else:
                    sentiment = None
                # ===================== 新增：生成消息对象 =====================
                msg_obj = {
                    "from": from_name,
                    "message": msg["message"],
                    "sentiment": sentiment,
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())  # 可选：时间戳
                }

                # === 同时保存到两种历史记录中确保一致性 ===
                # 方式1：使用成员排序元组作为键（与disconnect保持一致）
                sorted_key = tuple(sorted(the_guys))
                if sorted_key not in self.group_chat_history:
                    self.group_chat_history[sorted_key] = []
                self.group_chat_history[sorted_key].append(msg_obj)

                # === 保存到群聊历史 ===
                found, group_key = self.group.find_group(from_name)
                if found:
                    if group_key not in self.chat_history:   # 新建群历史
                        self.chat_history[group_key] = []
                    self.chat_history[group_key].append(msg_obj)

                # ===================== 新增：保存到临时聊天存储器 =====================
                if from_name not in self.chat_memory:
                    self.chat_memory[from_name] = []
                self.chat_memory[from_name].append(msg_obj)
                said2 = text_proc(msg["message"], from_name)

                # ===== 1. AI 不写入聊天记录 =====
                if from_name != "TomAI":
                    self.indices[from_name].add_msg_and_index(said2)

                # # ======== 保存完整群聊记录 ========
                # # 把一个群视为成员组成的 tuple key，使其可作为字典键
                # group_key = tuple(sorted(the_guys))

                # if group_key not in self.group_chat_history:
                #     self.group_chat_history[group_key] = []


                # # 保存记录（包含 emoji 情绪标签）
                # self.group_chat_history[group_key].append({
                #     "from": from_name,
                #     "message": msg["message"],
                #     "sentiment": sentiment,
                #     "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                # })

                # ===== 2. 向群组其他成员广播 =====
                for g in the_guys:
                    if g == from_name or g == "TomAI":
                        continue  # 发消息的人不重复写
                    to_sock = self.logged_name2sock[g]
                    # 发送消息并附加情绪
                    mysend(to_sock, json.dumps({
                        "action": "exchange",
                        "from": msg["from"],
                        "message": msg["message"],
                        "sentiment": sentiment
                    }))
                    # 写入对方索引
                    if g in self.indices:
                        self.indices[g].add_msg_and_index(said2)
                

#==============================================================================
#                 listing available peers
#==============================================================================
            elif msg["action"] == "list":
                from_name = self.logged_sock2name[from_sock]
                msg = self.group.list_all()
                mysend(from_sock, json.dumps({"action":"list", "results":msg}))
#==============================================================================
#             retrieve a sonnet
#==============================================================================
            elif msg["action"] == "poem":
                poem_indx = int(msg["target"])
                from_name = self.logged_sock2name[from_sock]
                print(from_name + ' asks for ', poem_indx)
                poem = self.sonnet.get_poem(poem_indx)
                poem = '\n'.join(poem).strip()
                print('here:\n', poem)
                mysend(from_sock, json.dumps({"action":"poem", "results":poem}))
#==============================================================================
#                 time
#==============================================================================
            elif msg["action"] == "time":
                ctime = time.strftime('%d.%m.%y,%H:%M', time.localtime())
                mysend(from_sock, json.dumps({"action":"time", "results":ctime}))
#==============================================================================
#                 search
#==============================================================================
            elif msg["action"] == "search":
                term = msg["target"]
                from_name = self.logged_sock2name[from_sock]
                print('search for ' + from_name + ' for ' + term)
                # search_rslt = (self.indices[from_name].search(term))
                search_rslt = '\n'.join([x[-1] for x in self.indices[from_name].search(term)])
                print('server side search: ' + search_rslt)
                mysend(from_sock, json.dumps({"action":"search", "results":search_rslt}))

#==============================================================================
#                 add a new member to my group
#==============================================================================
            elif msg["action"] == "add":
                from_name = self.logged_sock2name[from_sock]
                target = msg["target"]

                if not self.group.is_member(target):
                    mysend(from_sock, json.dumps({"action": "add", "status": "no-user"}))
                    return

                found, group_key = self.group.find_group(from_name)
                if not found:
                    self.group.connect(from_name, target)
                    mysend(from_sock, json.dumps({"action": "add", "status": "created"}))
                    return

                if target not in self.group.chat_grps[group_key]:
                    self.group.chat_grps[group_key].append(target)

                for member in self.group.chat_grps[group_key]:
                    if member != target:
                        sock_m = self.logged_name2sock[member]
                        mysend(sock_m, json.dumps({
                            "action": "connect",
                            "status": "success",
                            "from": target
                        }))

                to_sock = self.logged_name2sock[target]
                mysend(to_sock, json.dumps({
                    "action": "connect",
                    "status": "request",
                    "from": from_name
                }))
    
#==============================================================================
#                 AI query
#==============================================================================
            elif msg["action"] == "ai_query":
                from_name = self.logged_sock2name[from_sock]
                query = msg["query"]

                # ===== 关键：自动把 TomAI 拉进当前群聊（只拉一次）=====
                in_group, group_key = self.group.find_group(from_name)
                if in_group and "TomAI" not in self.group.chat_grps[group_key]:
                    self.group.chat_grps[group_key].append("TomAI")
                    print(f"TomAI 已被 {from_name} 召唤进入群聊")
                    for member in self.group.chat_grps[group_key]:
                        if member != "TomAI" and self.logged_name2sock[member] is not None:
                            mysend(self.logged_name2sock[member], json.dumps({
                                "action": "connect",
                                "status": "success",      
                                "from": "TomAI"           
                            }))

                # 调用 AI
                reply = self.call_remote_ai(query)
                reply = remove_emoji(reply)  # <- 这里去掉 TomAI 回复的 emoji   
                # 广播给当前群聊的所有人（包括提问者自己）
                the_guys = self.group.list_me(from_name)  # 包含 TomAI
                for g in the_guys:
                    if g == "TomAI":
                        continue  # 机器人自己不需要收到消息
                    to_sock = self.logged_name2sock[g]
                    mysend(to_sock, json.dumps({
                        "action": "exchange",
                        "from": "[TomAI]",
                        "message": reply
                    }))

#==============================================================================
# the "from" guy has had enough (talking to "to")!
#==============================================================================
            # elif msg["action"] == "disconnect":
            #     from_name = self.logged_sock2name[from_sock]
            #     the_guys = self.group.list_me(from_name)
            #     # ===== 获取群聊 key 取历史 =====
            #     group_key = tuple(sorted(the_guys + [from_name]))  # 包含自己
            #     history = self.group_chat_history.get(group_key, [])
            #     # ===== 返回记录给退出者 =====
            #     mysend(from_sock, json.dumps({
            #         "action": "history",
            #         "results": history  # list
            #     }))
            #     self.group.disconnect(from_name)
            #     the_guys.remove(from_name)
            #     if len(the_guys) == 1:  # only one left
            #         g = the_guys.pop()
            #         to_sock = self.logged_name2sock[g]
            #         mysend(to_sock, json.dumps({"action":"disconnect"}))
            elif msg["action"] == "disconnect":
                from_name = self.logged_sock2name[from_sock]
                the_guys = self.group.list_me(from_name)

                # 首先获取群组信息
                found, actual_group_key = self.group.find_group(from_name)

                # ===== 获取群聊历史记录 =====
                # 尝试从两种方式获取历史记录
                history = []

                # 方式1：使用成员排序元组作为键
                sorted_key = tuple(sorted(the_guys))
                if sorted_key in self.group_chat_history:
                    history = self.group_chat_history[sorted_key]
                
                # 方式2：如果方式1没有，则使用group.find_group返回的键
                if not history and found and actual_group_key in self.chat_history:
                    history = self.chat_history.get(actual_group_key, [])
                
                # # 修复：直接使用 the_guys 创建 group_key，不重复添加 from_name
                # group_key = tuple(sorted(the_guys))
                # history = self.group_chat_history.get(group_key, [])
                
                # # 如果没有找到历史记录，尝试从 chat_history 中查找
                # if not history:
                #     found, actual_group_key = self.group.find_group(from_name)
                #     if found:
                #         # 从 chat_history 获取历史记录
                #         history = self.chat_history.get(actual_group_key, [])
                
                # ===== 返回记录给退出者 =====
                mysend(from_sock, json.dumps({
                    "action": "history",
                    "results": history  # list
                }))
                
                # 清除该群聊的历史记录（可选）
                if sorted_key in self.group_chat_history:
                    del self.group_chat_history[sorted_key]
                
                if found and actual_group_key in self.chat_history:
                    del self.chat_history[actual_group_key]
                
                self.group.disconnect(from_name)
                the_guys.remove(from_name)
                if len(the_guys) == 1:  # only one left
                    g = the_guys.pop()
                    to_sock = self.logged_name2sock[g]
                    mysend(to_sock, json.dumps({"action":"disconnect"}))
                
            

#==============================================================================
#                 the "from" guy really, really has had enough
#==============================================================================

        else:
            #client died unexpectedly
            self.logout(from_sock)

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
