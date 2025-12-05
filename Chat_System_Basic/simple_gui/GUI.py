#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 30 13:36:58 2021

@author: bing
"""

# import all the required  modules
import threading
import select
import socket
from tkinter import *
from tkinter import font
from tkinter import ttk
from chat_utils import *
import json
from client_state_machine import ClientSM

from chat_bot_client import ChatBotClient



# GUI class for the chat
class GUI:
    # constructor method
    def __init__(self, send = None, recv= None, sm= None, s=None):
        # chat window which is currently hidden
        self.Window = Tk()
        self.Window.withdraw()
        self.send = send
        self.recv = recv
        self.sm = sm
        self.socket = s
        self.my_msg = ""
        self.system_msg = ""

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
          
        # create a Continue Button 
        # along with action
        self.go = Button(self.login,
                         text = "CONTINUE", 
                         font = "Helvetica 14 bold", 
                         command = lambda: self.goAhead(self.entryName.get()))
          
        self.go.place(relx = 0.4,
                      rely = 0.55)
        self.Window.mainloop()
  
    def goAhead(self, name):
        if len(name) > 0:
            msg = json.dumps({"action":"login", "name": name})
            self.send(msg)
            response = json.loads(self.recv())
            if response["status"] == 'ok':
                self.login.destroy()
                self.sm.set_state(S_LOGGEDIN)
                self.sm.set_myname(name)
                self.layout(name)
                self.textCons.config(state = NORMAL)
                # self.textCons.insert(END, "hello" +"\n\n")   
                self.textCons.insert(END, "You are logged in. Type commands or chat.\n\n")      
                self.textCons.config(state = DISABLED)
                self.textCons.see(END)
                # while True:
                #     self.proc()
        # the thread to receive messages
            process = threading.Thread(target=self.proc)
            process.daemon = True
            process.start()
  
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
          
        # create a scroll bar
        scrollbar = Scrollbar(self.textCons)

        # 在 self.labelHead 下方加入一个按钮

        self.botButton = Button(self.Window,
                        text = "🤖 ChatBot",
                        font = "Helvetica 10 bold",
                        bg = "#1D8348",
                        fg = "#ECF0F1",
                        command = self.openBotWindow)

        self.botButton.place(relx = 0.75, rely = 0.02, relwidth = 0.22, relheight = 0.04)
          
        # place the scroll bar 
        # into the gui window
        scrollbar.place(relheight = 1,
                        relx = 0.974)
          
        scrollbar.config(command = self.textCons.yview)
          
        self.textCons.config(state = DISABLED)
  
    # function to basically start the thread for sending messages
    def sendButton(self, msg):
        self.textCons.config(state = DISABLED)
        self.my_msg = msg
        # print(msg)
        self.entryMsg.delete(0, END)
        # 可选：GUI 本地显示正在发送的状态
        self.textCons.config(state=NORMAL)
        self.textCons.insert(END, f"Me: {msg}\n")
        self.textCons.config(state=DISABLED)

        # ⭐ 发送到服务器
        self.send(msg)
        

    def proc(self):
        # print(self.msg)
        while True:
            read, write, error = select.select([self.socket], [], [], 0)
            peer_msg = []
            # print(self.msg)
            if self.socket in read:
                peer_msg = self.recv()
            if len(self.my_msg) > 0 or len(peer_msg) > 0:
                # print(self.system_msg)
                self.system_msg += self.sm.proc(self.my_msg, peer_msg)
                self.my_msg = ""
                self.textCons.config(state = NORMAL)
                self.textCons.insert(END, self.system_msg +"\n\n")      
                self.textCons.config(state = DISABLED)
                self.textCons.see(END)

    def run(self):
        self.login()

    #openBotWindow 和 AI聊天处理
    def openBotWindow(self):
        bot = ChatBotClient()  # 创建 AI 客户端

        botWin = Toplevel()
        botWin.title("🤖 AI ChatBot")
        botWin.resizable(False, False)
        botWin.configure(width=400, height=500, bg="#1C2833")

        chatBox = Text(botWin, bg="#17202A", fg="#EAECEE", font="Helvetica 13")
        chatBox.place(relwidth=1, relheight=0.85)
        chatBox.config(state=DISABLED)

        inputBox = Entry(botWin, bg="#2C3E50", fg="#EAECEE", font="Helvetica 13")
        inputBox.place(relwidth=0.75, relheight=0.07, rely=0.87, relx=0.01)

        modeBox = ttk.Combobox(botWin, values=[
            "You are a friendly Python tutor.",
            "You are a strict professor who answers concisely.",
            "You are a humorous chatbot who jokes while answering.",
            "You are a poetic assistant who replies like a poem."
        ], font="Helvetica 10")
        modeBox.place(relx=0.01, rely=0.82, relwidth=0.75, relheight=0.05)
        modeBox.set("You are a friendly Python tutor.")  # Default personality

        def sendToBot():
            user_msg = inputBox.get()
            inputBox.delete(0, END)
            chatBox.config(state=NORMAL)
            chatBox.insert(END, "🧑 You: " + user_msg + "\n")
            chatBox.config(state=DISABLED)

            # ⭐⭐ 将人格设置进去（关键！）
            bot.messages = [{"role": "system", "content": modeBox.get()}]
        
            bot_reply = bot.chat(user_msg)
            chatBox.config(state=NORMAL)
            chatBox.insert(END, "🤖 Bot: " + bot_reply + "\n\n")
            chatBox.config(state=DISABLED)
            chatBox.see(END)

        sendBtn = Button(botWin, text="Send", font="Helvetica 10 bold",
                     bg="#566573", fg="#FDFEFE",
                     command=sendToBot)
        sendBtn.place(relx=0.78, rely=0.87, relwidth=0.21, relheight=0.07)
# create a GUI class object
if __name__ == "__main__":
    
    # 创建客户端 socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 5555))
    

    # 发送函数
    def send_msg(msg):
        try:
            mysend(client_socket, msg)
        except BrokenPipeError:
            print("⚠️ 服务器已断开连接")

    # 接收函数
    def recv_msg():
        try:
            return myrecv(client_socket)
        except Exception:
            return ""

    # 状态机对象
    sm = ClientSM(client_socket)

    # 创建 GUI 对象
    gui = GUI(send_msg, recv_msg, sm, client_socket)
    gui.run()
