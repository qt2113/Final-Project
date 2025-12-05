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
        # sonnet
        # self.sonnet_f = open('AllSonnets.txt.idx', 'rb')
        # self.sonnet = pkl.load(self.sonnet_f)
        # self.sonnet_f.close()
        #self.sonnet = indexer.PIndex("AllSonnets.txt")

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
                #said = msg["from"]+msg["message"]
                said2 = text_proc(msg["message"], from_name)
                self.indices[from_name].add_msg_and_index(said2)
                for g in the_guys[1:]:
                    to_sock = self.logged_name2sock[g]
                    self.indices[g].add_msg_and_index(said2)
                    mysend(to_sock, json.dumps({"action":"exchange", "from":msg["from"], "message":msg["message"]}))
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

                # 必须是在线用户
                if not self.group.is_member(target):
                    mysend(from_sock, json.dumps({"action": "add", "status": "no-user"}))
                    return

                # 找 from_name 所在的 group
                found, group_key = self.group.find_group(from_name)

                # 还没在群 → 先创建一个
                if not found:
                    self.group.connect(from_name, target)
                    mysend(from_sock, json.dumps({"action": "add", "status": "created"}))
                    return

                # 已有群 → 加入
                if target not in self.group.chat_grps[group_key]:
                    self.group.chat_grps[group_key].append(target)

                # 广播加入消息
                for member in self.group.chat_grps[group_key]:
                    if member != target:
                        sock_m = self.logged_name2sock[member]
                        mysend(sock_m, json.dumps({
                            "action": "connect",
                            "status": "success",
                            "from": target
                        }))

                # 通知被邀请者
                to_sock = self.logged_name2sock[target]
                mysend(to_sock, json.dumps({
                    "action": "connect",
                    "status": "request",
                    "from": from_name
                }))
    
#==============================================================================
# the "from" guy has had enough (talking to "to")!
#==============================================================================
            elif msg["action"] == "disconnect":
                from_name = self.logged_sock2name[from_sock]
                the_guys = self.group.list_me(from_name)
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
