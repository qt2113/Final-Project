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

from Chatbot_client import UnifiedChatClient
from server_actions import (
    handle_connect, handle_exchange, handle_ai_query,
    handle_disconnect, handle_time, handle_list, handle_search, handle_add, handle_summary, handle_keywords
)

# ==============================================================================
# AI Classes (Inheriting from UnifiedChatClient)
# ==============================================================================

class SentimentAI(UnifiedChatClient):
    def __init__(self):
        super().__init__(name="SentimentBot")
        self.system_prompt = {"role": "system", "content": "You are a sentiment analysis tool. You strictly analyze the emotion of the input text and return ONLY one word: positive, negative, or neutral."}
        self.messages = [self.system_prompt]

    def get_sentiment(self, text):
        self.messages = [self.system_prompt]
        
        prompt = f"Analyze the emotion of this sentence: '{text}'. Return ONLY: positive, negative, or neutral."
        try:
            resp = self.chat(prompt)
            resp = resp.lower().strip()
            if 'positive' in resp:
                return 'positive'
            elif 'negative' in resp:
                return 'negative'
            else:
                return 'neutral'
        except Exception as e:
            print(f"[SentimentAI] Error: {e}")
            return 'neutral'

class SummaryAI(UnifiedChatClient):
    def __init__(self):
        super().__init__(name="SummaryBot")
        self.system_prompt = {"role": "system", "content": "You are a helpful assistant capable of summarizing conversation history concisely."}
        self.messages = [self.system_prompt]

    def summarize_chat(self, chat_history):
        if not chat_history:
            return "No chat history available."
        
        self.messages = [self.system_prompt]
        
        prompt = "Please briefly summarize the main content of these chat logs:\n"
        recent_history = chat_history[-20:]
        for entry in recent_history:
            prompt += f"{entry['from']}: {entry['message']}\n"
        prompt += "\nSummary:"
        
        try:
            summary = self.chat(prompt)
            return summary.strip()
        except Exception as e:
            print(f"[SummaryAI] Error: {e}")
            return "Can't summarize the chat history."

class KeywordAI(UnifiedChatClient):
    def __init__(self):
        super().__init__(name="KeywordBot")
        self.system_prompt = {"role": "system", "content": "You are a keyword extraction tool."}
        self.messages = [self.system_prompt]

    def get_keywords(self, chat_history):
        if not chat_history:
            return "No chat history available."
            
        self.messages = [self.system_prompt]
        
        prompt = "Please extract 3–5 of the most important keywords or hashtags from the following chat history, separated by commas:\n"
        recent_history = chat_history[-20:]
        for entry in recent_history:
            prompt += f"{entry['from']}: {entry['message']}\n"
        prompt += "\nKeywords:"
        
        try:
            keywords = self.chat(prompt)
            return keywords.strip()
        except Exception as e:
            print(f"[KeywordAI] Error: {e}")
            return "Can't extract keywords from the chat history."

# ==============================================================================
# Server Class
# ==============================================================================

class Server:
    def __init__(self):
        self.new_clients = [] 
        self.logged_name2sock = {} 
        self.logged_sock2name = {} 
        self.all_sockets = []
        self.group = grp.Group()
        
        # start server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(SERVER)
        self.server.listen(5)
        self.all_sockets.append(self.server)
        
        self.indices = {}
        self.chat_history = {} 
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

        # === AI Modules Initialization ===
        self.sentiment_ai = SentimentAI()
        self.summary_ai = SummaryAI()
        self.keyword_ai = KeywordAI()

        self.tom_ai = UnifiedChatClient(name="TomAI")   
        self.ai_name = "TomAI"
        
        self.logged_name2sock[self.ai_name] = None       
        self.logged_sock2name[None] = self.ai_name      
        print("TomAI has joined the chat system.")

    def call_remote_ai(self, query):
        try:
            return self.tom_ai.chat(query)
        except Exception as e:
            return f"TomAI is temporarily unavailable: {e}"
            
    def new_client(self, sock):
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

            if getattr(user_idx, "password_hash", None):
                if not user_idx.check_password(password_received):
                    del self.logged_name2sock[name]
                    del self.logged_sock2name[sock]
                    mysend(sock, json.dumps({"action": "login", "status": "wrong-password"}))
                    return
            else:
                user_idx.set_password(password_received)

            print(f"{name} logged in")
            self.group.join(name)
            mysend(sock, json.dumps({"action": "login", "status": "ok", "name": name}))

        except Exception as e:
            print("login exception:", e)

    def logout(self, sock):
        name = self.logged_sock2name[sock]
        pkl.dump(self.indices[name], open(name + '.idx','wb'))
        del self.indices[name]
        del self.logged_name2sock[name]
        del self.logged_sock2name[sock]
        self.all_sockets.remove(sock)
        self.group.leave(name)
        sock.close()

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
            print("Unknown action:", action)

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

    def run(self):
        print ('starting server...')
        while(1):
           read, write, error = select.select(self.all_sockets, [], [])
           for logc in list(self.logged_name2sock.values()):
               if logc in read:
                   self.handle_msg(logc)
           for newc in self.new_clients[:]:
               if newc in read:
                   self.login(newc)
           if self.server in read :
               sock, address = self.server.accept()
               self.new_client(sock)

def main():
    server = Server()
    server.run()

if __name__ == "__main__":
    main()