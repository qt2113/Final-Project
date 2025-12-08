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
    handle_disconnect, handle_time, handle_list, handle_search, handle_add,handle_summary,handle_keywords
)

class AI:
    def __init__(self):
        from Chatbot_client import ChatBotClientOpenAI
        self.llm = ChatBotClientOpenAI()
    
    def get_sentiment(self, text):
        """
        Use LLM to analyze sentiment of the text, return 'positive', 'negative', or 'neutral'  
        """
        prompt = f"Please judge the emotion of this sentence: {text}。ONLY return: positive/negative/neutral"
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
            print("Failed to analyze the sentiment:", e)
            return 'neutral'
    def summarize_chat(self, chat_history):
        """
        Use LLM to summarize the chat history
        """
        if not chat_history:
            return "No chat history available."
            
        prompt = "Please briefly summarize the main content of these chat history:\n"
        recent_history = chat_history[-20:] 
        for entry in recent_history:
            prompt += f"{entry['from']}: {entry['message']}\n"
        prompt += "Summary:"
        
        try:
            summary = self.llm.chat(prompt)
            return summary.strip()
        except Exception as e:
            print("Failed to summarize:", e)
            return "Can't summarize the chat history."

    def get_keywords(self, chat_history):
        """
        Use LLM to extract keywords from chat history
        """
        if not chat_history:
            return "No chat history available."
            
        prompt = "Please extract 3–5 of the most important keywords or hashtags from the following chat history, separated by commas:\n"
        recent_history = chat_history[-20:]
        for entry in recent_history:
            prompt += f"{entry['from']}: {entry['message']}\n"
        prompt += "Key words:"
        
        try:
            keywords = self.llm.chat(prompt)
            return keywords.strip()
        except Exception as e:
            print("Failed to extract the key words", e)
            return "Can't extract keywords from the chat history."

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
        self.ai = AI()  
        self.group_chat_history = {} 
        self.chat_memory = {}
                
        self.ACTION_MAP = {
            "connect": handle_connect,
            "exchange": handle_exchange,
            "ai_query": handle_ai_query,
            "disconnect": handle_disconnect,
            "time": handle_time,
            "list": handle_list,
            "add": handle_add,
            "summary": handle_summary,
            "keywords": handle_keywords
            }

        self.tom_ai = ChatBotClientOpenAI()   
        self.ai_name = "TomAI"
        self.logged_name2sock[self.ai_name] = None       
        self.logged_sock2name[None] = self.ai_name      
        print("TomAI has joined the chat system.")

    def call_remote_ai(self, query):
            try:
                return self.tom_ai.chat(query)
            except Exception as e:
                return f"TomAI is temporarily unavailable{e}"
            
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
            password_received = msg.get("password", "")  

            if self.group.is_member(name):
                mysend(sock, json.dumps({"action": "login", "status": "duplicate"}))
                return

            if sock in self.new_clients:
                self.new_clients.remove(sock)

            self.logged_name2sock[name] = sock
            self.logged_sock2name[sock] = name

            if name not in self.indices:
                try:
                    self.indices[name] = pkl.load(open(f"{name}.idx", "rb"))
                except (IOError, EOFError, pkl.UnpicklingError):
                    self.indices[name] = indexer.Index(name)

            user_idx = self.indices[name]

            # === Password Handling ===
            password_hash = getattr(user_idx, "password_hash", None)

            if password_hash:
                # Existing user: verify password
                if not user_idx.check_password(password_received):
                    del self.logged_name2sock[name]
                    del self.logged_sock2name[sock]
                    mysend(sock, json.dumps({"action": "login", "status": "wrong-password"}))
                    return
            else:
                # New user: set password
                user_idx.set_password(password_received)

            # Login successfully
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
            return
        action = msg.get("action")
        handler = self.ACTION_MAP.get(action)
        if handler:
            handler(self, from_sock, msg)   
        else:
            print("Unkown action:", action)

    def broadcast_to_peers(self, sender_name, msg_json_str):
        _, gkey = self.group.find_group(sender_name)
        if gkey not in self.group.chat_grps:
            return
        for name in self.group.chat_grps[gkey]:
            if name == "TomAI":      
                continue
            sock = self.logged_name2sock.get(name)
            if sock:
                mysend(sock, msg_json_str)   

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
