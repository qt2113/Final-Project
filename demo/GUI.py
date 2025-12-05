#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 30 13:36:58 2021

@author: bing
"""

# import all the required  modules
import threading
import select
from tkinter import *
from tkinter import font
from tkinter import ttk
from chat_utils import *
import json
import time
from tkinter import messagebox

# GUI class for the chat
class GUI:
    # constructor method
    def __init__(self, send, recv, sm, s, chatbot):
        # chat window which is currently hidden
        self.Window = Tk()
        self.Window.withdraw()
        self.send = send
        self.recv = recv
        self.sm = sm
        self.socket = s
        self.my_msg = ""
        self.system_msg = ""
        self.chatbot = chatbot
         # track if proc thread started
        self.proc_thread = None

    def login(self):
        # login window
        self.login = Toplevel()
        # set the title
        self.login.title("Login")
        self.login.resizable(width = False, 
                             height = False)
        self.login.configure(width = 400,
                             height = 300)
        # create a Label
        self.pls = Label(self.login, 
                       text = "Please login to continue",
                       justify = CENTER, 
                       font = "Helvetica 14 bold")
          
        self.pls.place(relheight = 0.15,
                       relx = 0.2, 
                       rely = 0.07)
        # create a Label
        self.labelName = Label(self.login,
                               text = "Name: ",
                               font = "Helvetica 12")
          
        self.labelName.place(relheight = 0.2,
                             relx = 0.1, 
                             rely = 0.2)
          
        # create a entry box for 
        # tyoing the message
        self.entryName = Entry(self.login, 
                             font = "Helvetica 14")
          
        self.entryName.place(relwidth = 0.4, 
                             relheight = 0.12,
                             relx = 0.35,
                             rely = 0.2)
          
        # set the focus of the curser
        self.entryName.focus()
        
        # Password label
        self.labelPwd = Label(self.login,
                            text = "Password: ",
                            font = "Helvetica 12")

        self.labelPwd.place(relheight = 0.2,
                            relx = 0.1,
                            rely = 0.35)

        # Password Entry
        self.entryPwd = Entry(self.login,
                            font = "Helvetica 14",
                            show="*")

        self.entryPwd.place(relwidth = 0.4,
                            relheight = 0.12,
                            relx = 0.35,
                            rely = 0.35)

          
        # create a Continue Button 
        # along with action
        self.go = Button(self.login,
                         text = "CONTINUE", 
                         font = "Helvetica 14 bold", 
                         command = lambda: self.goAhead(self.entryName.get()))
          
        self.go.place(relx = 0.4,
                      rely = 0.55)
        #self.Window.mainloop()
  
    def goAhead(self, name):
        name = self.entryName.get().strip()
        pwd = self.entryPwd.get()
        if len(name) == 0 or len(pwd) == 0:
            return  
        if len(name) > 0:
            msg = json.dumps({"action": "login", "name": name, "password": pwd})
            try:
                self.send(msg)
            except Exception as e:
                messagebox.showerror("Network", f"Failed to send login: {e}")
                return
            threading.Thread(
                target=self.wait_login_response,
                args=(name,),   # 必须传入参数！
                daemon=True
            ).start()
        #     response = json.loads(self.recv())
        #     if response["status"] == 'ok':
        #         self.login.destroy()
        #         self.sm.set_state(S_LOGGEDIN)
        #         self.sm.set_myname(name)
        #         self.layout(name)
        #         self.textCons.config(state = NORMAL)
        #         # self.textCons.insert(END, "hello" +"\n\n")   
        #         self.textCons.insert(END, menu +"\n\n")      
        #         self.textCons.config(state = DISABLED)
        #         self.textCons.see(END)
        #         # while True:
        #         #     self.proc()
        # # the thread to receive messages
        #     process = threading.Thread(target=self.proc)
        #     process.daemon = True
        #     process.start()  
  
    # The main layout of the chat
    def layout(self,name):
        
        self.name = name
        # to show chat window
        self.Window.deiconify()
        self.Window.title("CHATROOM")
        self.Window.resizable(width = False,
                              height = False)
        self.Window.configure(width = 470,
                              height = 550,
                              bg = "#17202A")
        self.labelHead = Label(self.Window,
                             bg = "#17202A", 
                              fg = "#EAECEE",
                              text = self.name ,
                               font = "Helvetica 13 bold",
                               pady = 5)
          
        self.labelHead.place(relwidth = 1)
        self.line = Label(self.Window,
                          width = 450,
                          bg = "#ABB2B9")
          
        self.line.place(relwidth = 1,
                        rely = 0.07,
                        relheight = 0.012)
          
        self.textCons = Text(self.Window,
                             width = 20, 
                             height = 2,
                             bg = "#17202A",
                             fg = "#EAECEE",
                             font = "Helvetica 14", 
                             padx = 5,
                             pady = 5)
          
        self.textCons.place(relheight = 0.745,
                            relwidth = 1, 
                            rely = 0.08)
          
        self.labelBottom = Label(self.Window,
                                 bg = "#ABB2B9",
                                 height = 80)
          
        self.labelBottom.place(relwidth = 1,
                               rely = 0.825)
          
        self.entryMsg = Entry(self.labelBottom,
                              bg = "#2C3E50",
                              fg = "#EAECEE",
                              font = "Helvetica 13")
          
        # place the given widget
        # into the gui window
        self.entryMsg.place(relwidth = 0.74,
                            relheight = 0.06,
                            rely = 0.008,
                            relx = 0.011)
          
        self.entryMsg.focus()
          
        # create a Send Button
        self.buttonMsg = Button(self.labelBottom,
                                text = "Send",
                                font = "Helvetica 10 bold", 
                                width = 20,
                                bg = "#ABB2B9",
                                command = lambda : self.sendButton(self.entryMsg.get()))
          
        self.buttonMsg.place(relx = 0.77,
                             rely = 0.008,
                             relheight = 0.06, 
                             relwidth = 0.22)
          
        self.textCons.config(cursor = "arrow")

        self.btnAI = Button(self.labelBottom,
                            text="AI Chat",
                            font="Helvetica 10 bold",
                            bg="#2E86C1",
                            fg="white",
                            command=self.open_ai_window)
        self.btnAI.place(relx=0.53, rely=0.008, relheight=0.06, relwidth=0.22)

          
        # create a scroll bar
        scrollbar = Scrollbar(self.textCons)
          
        # place the scroll bar 
        # into the gui window
        scrollbar.place(relheight = 1,
                        relx = 0.974)
          
        scrollbar.config(command = self.textCons.yview)
          
        self.textCons.config(state = DISABLED)

        # ==== 群聊按钮 ====
        self.btnGroup = Button(
            self.labelBottom,
            text="Group Chat",
            font="Helvetica 10 bold",
            bg="#6C3483",
            fg="white",
            command=self.group_chat
        )
        self.btnGroup.place(relx=0.77, rely=0.08, relheight=0.05, relwidth=0.22)

    def group_chat(self):
        """Enter group chat with ALL online users."""
        msg = json.dumps({
            "action": "connect",
            "target": "ALL"
        })
        self.send(msg)

  
    # function to basically start the thread for sending messages
    def sendButton(self, msg):
        self.textCons.config(state = DISABLED)
        self.my_msg = msg
        # print(msg)
        self.entryMsg.delete(0, END)

    def _on_login_success(self, name):
        """在主线程执行的登录成功回调（通过 after 调用）"""
        try:
            if hasattr(self, "login") and self.login:
                self.login.destroy()
        except Exception:
            pass

        self.sm.set_state(S_LOGGEDIN)
        self.sm.set_myname(name)
        self.layout(name)
        # show menu
        self.textCons.config(state = NORMAL)
        try:
            self.textCons.insert(END, menu +"\n\n")
        except Exception:
            self.textCons.insert(END, "\n\n")
        self.textCons.config(state = DISABLED)
        self.textCons.see(END)

        # start proc thread if not started
        if self.proc_thread is None or not self.proc_thread.is_alive():
            self.proc_thread = threading.Thread(target=self.proc, daemon=True)
            self.proc_thread.start()

    def _on_login_failed(self, reason):
        """在主线程执行的登录失败回调"""
        messagebox.showerror("Login failed", reason)

    # ===========================
    #   AI ChatBot 独立窗口函数
    # ===========================

    def open_ai_window(self):
        # 如果窗口已存在，则抬到前面
        if hasattr(self, "ai_win") and self.ai_win.winfo_exists():
            self.ai_win.lift()
            return

        self.ai_win = Toplevel(self.Window)
        self.ai_win.title("Chat with TomAI")
        self.ai_win.geometry("520x560")
        self.ai_win.configure(bg="#1C2833")

        # ====== 1. 上方聊天显示区 ======
        self.ai_text = Text(
            self.ai_win,
            state=DISABLED, wrap=WORD,
            bg="#17202A", fg="#EAECEE",
            font="Helvetica 13", relief=FLAT
        )
        self.ai_text.pack(fill=BOTH, expand=True, padx=8, pady=(8, 0))

        # ====== 2. 人格选择区 ======
        persona_frame = Frame(self.ai_win, bg="#1C2833")
        persona_frame.pack(fill=X, padx=8, pady=(6, 6))

        Label(
            persona_frame, text="AI Personality:",
            fg="white", bg="#1C2833",
            font="Helvetica 10 bold"
        ).pack(side=LEFT, padx=(0, 6))

        self.persona_box = ttk.Combobox(
            persona_frame,
            values=[
                "You are a friendly Python tutor.",
                "You are a strict professor who answers concisely.",
                "You are a humorous chatbot who jokes while answering.",
                "You are a poetic assistant who replies like a poem.",
            ],
            font="Helvetica 10",
            state="readonly"
        )
        self.persona_box.set("You are a friendly Python tutor.")
        self.persona_box.pack(side=LEFT, fill=X, expand=True)

        # ====== 3. 输入框 + 发送按钮区域 ======
        bottom = Frame(self.ai_win, bg="#1C2833")
        bottom.pack(fill=X, padx=8, pady=(0, 10))

        # 输入框
        self.ai_entry = Entry(
            bottom,
            font="Helvetica 12",
            bg="#2C3E50", fg="white",
            relief=FLAT
        )
        self.ai_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        self.ai_entry.bind("<Return>", lambda e: self.ai_send_button())

        # 发送按钮
        Button(
            bottom,
            text="Send",
            command=self.ai_send_button,
            bg="#566573", fg="#FDFEFE",
            font="Helvetica 10 bold",
            relief=GROOVE
        ).pack(side=RIGHT)


    def ai_send_button(self):
        text = self.ai_entry.get().strip()
        if not text:
            return

        self._ai_append(f"[You] {text}")
        self.ai_entry.delete(0, END)

        # 异步防卡死
        import threading
        threading.Thread(
            target=self._ai_call_and_display,
            args=(text,),
            daemon=True
        ).start()


    def _ai_append(self, msg):
        """线程安全地往 AI 文本区域写入"""
        def append():
            self.ai_text.config(state=NORMAL)
            self.ai_text.insert(END, msg + "\n")
            self.ai_text.see(END)
            self.ai_text.config(state=DISABLED)
        self.ai_text.after(0, append)


    def _ai_call_and_display(self, user_text):
        try:
            # ⭐ 每次对话前重置人格 System prompt
            persona = self.persona_box.get()
            self.chatbot.messages = [{"role": "system", "content": persona}]

            reply = self.chatbot.chat(user_text)
            self._ai_append(f"[TomAI] {reply}")

        except Exception as e:
            self._ai_append(f"[系统错误] Chatbot 调用失败: {e}")

    
    def goAhead_blocking_alternative(self):
        """
        (保留，不被使用) 如果将来需要短超时的同步方式，可以实现 select + 非阻塞 recv。
        目前使用后台线程方式，因此不使用此函数。
        """
        pass

    def wait_login_response(self, requested_name):
        try:
            raw = self.recv()
        except Exception as e:
            self.Window.after(0, lambda: self._on_login_failed(f"Network error: {e}"))
            return

        if not raw:
            self.Window.after(0, lambda: self._on_login_failed("No response from server."))
            return

        try:
            response = json.loads(raw)
        except Exception as e:
            self.Window.after(0, lambda: self._on_login_failed(f"Invalid response: {e}"))
            return

        status = response.get("status")

        if status == "ok":
            name = response.get("name", requested_name)
            self.Window.after(0, lambda: self._on_login_success(name))

        elif status == "wrong-password":
            self.Window.after(0, lambda: self._on_login_failed("Wrong password."))

        elif status == "duplicate":
            self.Window.after(0, lambda: self._on_login_failed("User already logged in."))

        else:
            self.Window.after(0, lambda: self._on_login_failed(
                f"Unknown login status: {status}"
            ))


    def proc(self):
        # print(self.msg)
        while True:
            time.sleep(0.1)
            read, write, error = select.select([self.socket], [], [], 0)
            peer_msg = []
            # print(self.msg)
            if self.socket in read:
                peer_msg = self.recv()
                try:
                    msg = json.loads(peer_msg)

                    # 群聊被创建（来自 server）
                    if msg.get("action") == "connect" and msg.get("status") == "group-created":
                        self.system_msg += f"*** Group created. Creator: {msg.get('from')} ***\n"

                    # 有人加入群聊
                    if msg.get("action") == "connect" and msg.get("status") == "success":
                        self.system_msg += f"*** Join the group ***\n"

                    # 有人向我发起连接请求（两人模式）
                    if msg.get("action") == "connect" and msg.get("status") == "request":
                        self.system_msg += f"*** {msg.get('from')} invite you to chat ***\n"

                    if msg.get("action") == "exchange":
                        sender = msg.get("from")
                        content = msg.get("message")
                        sentiment = msg.get("sentiment", "neutral")

                        # 根据情绪添加 emoji
                        if sentiment == "positive":
                            emoji = "😊"
                        elif sentiment == "negative":
                            emoji = "😢"
                        else:
                            emoji = "😐"

                        self.system_msg += f"[{sender}] {content} {emoji} \n"
                        #handled = True

                #except:
                #    pass
                except Exception as e:
                    self.system_msg += f"[系统错误] 解析消息失败: {e}\n"
                    #handled = True
                #if not handled:
                    #self.system_msg += self.sm.proc(self.my_msg, peer_msg)

            bot_response = None
            if "@AI_bot" in self.my_msg:
                parts = self.my_msg.split("@AI_bot", 1)
                query = parts[1].strip() if len(parts) > 1 else ""
                
                if query:  # 有问题才发
                    mysend(self.socket, json.dumps({
                        "action": "ai_query",
                        "query": query
                    }))
                    self.my_msg = self.my_msg.replace("@AI_bot", "", 1).strip()                   
                else:
                    pass

            if len(self.my_msg) > 0 or len(peer_msg) > 0:
                # print(self.system_msg)
                if len(self.my_msg) > 0 or len(peer_msg) > 0:
                    self.system_msg += self.sm.proc(self.my_msg, peer_msg)
                self.my_msg = ""
                self.textCons.config(state = NORMAL)
                self.textCons.insert(END, self.system_msg +"\n\n")      
                self.textCons.config(state = DISABLED)
                self.system_msg = ""
                self.textCons.see(END)

    def run(self):
        self.login()
        self.Window.mainloop()
# create a GUI class object
if __name__ == "__main__": 
    g = GUI()