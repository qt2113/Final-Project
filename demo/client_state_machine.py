"""
Created on Sun Apr  5 00:00:32 2015

@author: zhengzhang
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

    def set_state(self, state):
        self.state = state

    def get_state(self):
        return self.state

    def set_myname(self, name):
        self.me = name

    def get_myname(self):
        return self.me

    def connect_to(self, peer):
        # group chat
        if peer.upper() == "ALL":
            msg = json.dumps({"action": "connect", "target": "ALL"})
            mysend(self.s, msg)
            self.peer = "ALL"
            self.out_msg += "You are now creating a group chat...\n"
            return True
        # one-on-one chat
        msg = json.dumps({"action":"connect", "target":peer})
        mysend(self.s, msg)
        response = json.loads(myrecv(self.s))
        if response["status"] == "success":
            self.peer = peer
            self.state = S_CHATTING
            self.out_msg += 'You are connected with '+ self.peer + '\n'
            return (True)
        elif response["status"] == "busy":
            self.out_msg += 'User is busy. Please try again later\n'
        elif response["status"] == "self":
            self.out_msg += 'Cannot talk to yourself (sick)\n'
        else:
            self.out_msg += 'User is not online, try again later\n'
        return(False)

    def disconnect(self):
        msg = json.dumps({"action":"disconnect"})
        mysend(self.s, msg)
        self.out_msg += 'You are disconnected from ' + self.peer + '\n'
        self.peer = ''

    def proc(self, my_msg, peer_msg):
        self.out_msg = ''
#==============================================================================
# Once logged in, do a few things: get peer listing, connect, search
# And, of course, if you are so bored, just go
# This is event handling instate "S_LOGGEDIN"
#==============================================================================
        if self.state == S_LOGGEDIN:
            # todo: can't deal with multiple lines yet
            if len(my_msg) > 0:

                if my_msg == 'q':
                    self.out_msg += 'See you next time!\n'
                    self.state = S_OFFLINE

                elif my_msg == 'time':
                    mysend(self.s, json.dumps({"action":"time"}))
                    time_in = json.loads(myrecv(self.s))["results"]
                    self.out_msg += "Time is: " + time_in

                elif my_msg == 'who':
                    mysend(self.s, json.dumps({"action":"list"}))
                    logged_in = json.loads(myrecv(self.s))["results"]
                    self.out_msg += 'Here are all the users in the system:\n'
                    self.out_msg += logged_in

                elif my_msg[0] == '@':
                    peer = my_msg[1:]
                    peer = peer.strip()
                    if self.connect_to(peer) == True:
                        self.state = S_CHATTING
                        self.out_msg += 'Connect to ' + peer + '. Chat away!\n\n'
                        self.out_msg += '-----------------------------------\n'
                    else:
                        self.out_msg += 'Connection unsuccessful\n'

                elif my_msg[0] == '?':
                    term = my_msg[1:].strip()
                    mysend(self.s, json.dumps({"action":"search", "target":term}))
                    search_rslt = json.loads(myrecv(self.s))["results"].strip()
                    if (len(search_rslt)) > 0:
                        self.out_msg += search_rslt + '\n\n'
                    else:
                        self.out_msg += '\'' + term + '\'' + ' not found\n\n'

                elif my_msg[0] == 'p' and my_msg[1:].isdigit():
                    poem_idx = my_msg[1:].strip()
                    mysend(self.s, json.dumps({"action":"poem", "target":poem_idx}))
                    poem = json.loads(myrecv(self.s))["results"]
                    # print(poem)
                    if (len(poem) > 0):
                        self.out_msg += poem + '\n\n'
                    else:
                        self.out_msg += 'Sonnet ' + poem_idx + ' not found\n\n'

                else:
                    self.out_msg += menu

            if len(peer_msg) > 0:
                peer_msg = json.loads(peer_msg)
                if peer_msg["action"] == "connect":
                    self.peer = peer_msg["from"]
                    self.out_msg += 'Request from ' + self.peer + '\n'
                    self.out_msg += 'You are connected with ' + self.peer
                    self.out_msg += '. Chat away!\n\n'
                    self.out_msg += '------------------------------------\n'
                    self.state = S_CHATTING

#==============================================================================
# Start chatting, 'bye' for quit
# This is event handling instate "S_CHATTING"
#==============================================================================
        elif self.state == S_CHATTING:
            if len(my_msg) > 0:     # my stuff going out
                if my_msg.startswith("@TomAI"):
                    query = my_msg[6:].strip()
                    if query:
                        mysend(self.s, json.dumps({"action": "ai_query", "query": query}))
                        self.my_msg = ""        
                        return self.out_msg     

                elif my_msg.startswith("add "):
                    new_user = my_msg[4:].strip()
                    mysend(self.s, json.dumps({"action": "add", "target": new_user}))
                    return self.out_msg

                elif my_msg == 'bye':
                    mysend(self.s, json.dumps({"action":"exchange", "from":"[" + self.me + "]", "message":"bye"}))
                    # self.disconnect()
                    # self.state = S_LOGGEDIN
                    # self.peer = ''
                    return self.out_msg
                
                elif my_msg == '/summary':
                    mysend(self.s, json.dumps({"action":"summary"}))
                    # 注意：这里不直接 recv，而是让主循环的 peer_msg 处理返回结果
                    # 但原代码采用了同步等待 recv 的写法，为了保持一致性：
                    summary_msg = json.loads(myrecv(self.s))["results"]
                    self.out_msg += "\n===== 💬 Chat Summary =====\n"
                    self.out_msg += summary_msg + "\n===========================\n\n"
                    return self.out_msg

                # [新增] Keywords 命令
                elif my_msg == '/keywords':
                    mysend(self.s, json.dumps({"action":"keywords"}))
                    # 同步等待结果
                    keywords_msg = json.loads(myrecv(self.s))["results"]
                    self.out_msg += "\n===== 🔑 Chat Keywords =====\n"
                    self.out_msg += keywords_msg + "\n==========================\n\n"
                    return self.out_msg
                
                else:
                    mysend(self.s, json.dumps({"action":"exchange", "from":"[" + self.me + "]", "message":my_msg}))
                    self.out_msg += f"[{self.me}]: {my_msg}\n"

                self.my_msg = ""
                return self.out_msg  

            if len(peer_msg) > 0:    # peer's stuff, coming in
                peer_msg = json.loads(peer_msg)
                if peer_msg["action"] == "connect" and peer_msg.get("status")=="request":
                    self.out_msg += f"({peer_msg['from']} joined the chat)\n"

                # 普通聊天消息（群聊/单聊都适用）
                elif peer_msg["action"] == "exchange":
                    sender = peer_msg.get("from")
                    content = peer_msg.get("message")
                    sentiment = peer_msg.get("sentiment", "neutral")                    
                    if sender != "[TomAI]":
                        if sentiment == "positive":
                            emoji = "😊"
                        elif sentiment == "negative":
                            emoji = "😢"
                        elif sentiment == "neutral":
                            emoji = "😐"
                        else:
                            emoji = ""
                        content_display = f' {emoji}'
                    else:
                        content_display = ''
                    self.out_msg += peer_msg["from"] + peer_msg["message"] + f'{content_display}\n'
                
                elif peer_msg["action"] == "history":
                    history_list = peer_msg.get("results", [])
                    self.out_msg += "\n===== 群聊历史记录 =====\n"
                    for record in history_list:
                        sender = record.get("from")
                        content = record.get("message")
                        sentiment = record.get("sentiment", "neutral")
                        timestamp = record.get("timestamp")
                        # 显示格式
                        self.out_msg += f"{timestamp} {sender}: {content}\n"
                    self.out_msg += "===== 聊天记录结束 =====\n\n"                    

                elif peer_msg["action"] == "summary":
                    self.out_msg += "\n===== 💬 Chat Summary =====\n"
                    self.out_msg += peer_msg["results"] + "\n===========================\n"
                
                elif peer_msg["action"] == "keywords":
                    self.out_msg += "\n===== 🔑 Chat Keywords =====\n"
                    self.out_msg += peer_msg["results"] + "\n==========================\n"
                    
                elif peer_msg["action"] == "disconnect":
                    self.out_msg += 'You are disconnected from ' + self.peer + '\n'
                    self.state = S_LOGGEDIN
                    self.peer = ''



            # Display the menu again
            if self.state == S_LOGGEDIN:
                self.out_msg += menu
#==============================================================================
# invalid state
#==============================================================================
        else:
            self.out_msg += 'How did you wind up here??\n'
            print_state(self.state)

        return self.out_msg
