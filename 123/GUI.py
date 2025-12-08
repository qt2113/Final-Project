#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import select
import json
import time
import hashlib
from tkinter import *
from tkinter import ttk, font, messagebox
from chat_utils import *
from image_generator import ImageGenerator


class GUI:
    def __init__(self, send, recv, sm, s, chatbot):
        self.Window = Tk()
        self.Window.withdraw()

        self.send = send
        self.recv = recv
        self.sm = sm
        self.socket = s
        self.chatbot = chatbot

        self.my_msg = ""
        self.system_msg = ""
        self.proc_thread = None

        # 用于独立图片生成窗口
        self.img_gen = ImageGenerator()

    # ======================================================
    # 登录窗口
    # ======================================================
    def login(self):
        self.login = Toplevel()
        self.login.title("Login")
        self.login.geometry("400x300")
        self.login.resizable(False, False)

        Label(self.login, text="Please login to continue",
              font="Helvetica 14 bold").place(relx=0.2, rely=0.07)

        Label(self.login, text="Name:", font="Helvetica 12").place(relx=0.1, rely=0.2)
        self.entryName = Entry(self.login, font="Helvetica 14")
        self.entryName.place(relx=0.35, rely=0.2, relwidth=0.4)
        self.entryName.focus()

        Label(self.login, text="Password:", font="Helvetica 12").place(relx=0.1, rely=0.35)
        self.entryPwd = Entry(self.login, font="Helvetica 14", show="*")
        self.entryPwd.place(relx=0.35, rely=0.35, relwidth=0.4)

        Button(self.login, text="CONTINUE", font="Helvetica 14 bold",
               command=lambda: self.goAhead(self.entryName.get())
               ).place(relx=0.4, rely=0.55)

    def goAhead(self, name):
        name = self.entryName.get().strip()
        pwd = self.entryPwd.get()
        if not name or not pwd:
            return

        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
        msg = json.dumps({"action": "login", "name": name, "password": pwd_hash})

        try:
            self.send(msg)
        except:
            messagebox.showerror("Network", "Login request failed.")
            return

        threading.Thread(target=self.wait_login_response,
                         args=(name,), daemon=True).start()

    # 监听服务器的登录结果：
    def wait_login_response(self, requested_name):
        raw = self.recv()
        if not raw:
            self.Window.after(0,
                lambda: messagebox.showerror("Login failed", "No response from server."))
            return
        try:
            res = json.loads(raw)
        except:
            self.Window.after(0,
                lambda: messagebox.showerror("Login failed", "Invalid server response."))
            return

        status = res.get("status")

        if status == "ok":
            name = res.get("name", requested_name)
            self.Window.after(0, lambda: self._on_login_success(name))
        elif status == "wrong-password":
            self.Window.after(0,
                lambda: messagebox.showerror("Login failed", "Wrong password."))
        elif status == "duplicate":
            self.Window.after(0,
                lambda: messagebox.showerror("Login failed", "User already logged in."))
        else:
            self.Window.after(0,
                lambda: messagebox.showerror("Login failed",
                                             f"Unknown status: {status}"))

    def _on_login_success(self, name):
        self.login.destroy()
        self.sm.set_state(S_LOGGEDIN)
        self.sm.set_myname(name)
        self.layout(name)

        # 主界面开始消息处理线程
        if not self.proc_thread:
            self.proc_thread = threading.Thread(target=self.proc, daemon=True)
            self.proc_thread.start()

    # ======================================================
    # 主聊天界面布局
    # ======================================================
    def layout(self, name):
        self.name = name
        self.Window.deiconify()
        self.Window.title("Chatroom")
        self.Window.geometry("470x550")
        self.Window.configure(bg="#17202A")
        self.Window.resizable(False, False)

        # 顶部 Label
        Label(self.Window, bg="#17202A", fg="#EAECEE",
              text=self.name, font="Helvetica 13 bold",
              pady=5).place(relwidth=1)

        Label(self.Window, bg="#ABB2B9").place(relwidth=1, rely=0.07, relheight=0.012)

        # 聊天文本区
        self.textCons = Text(self.Window, bg="#17202A", fg="#EAECEE",
                             font="Helvetica 14", padx=5, pady=5)
        self.textCons.place(relheight=0.745, relwidth=1, rely=0.08)
        self.textCons.config(state=DISABLED)

        # 滚动条
        scrollbar = Scrollbar(self.textCons)
        scrollbar.place(relheight=1, relx=0.974)
        scrollbar.config(command=self.textCons.yview)

        # 底部输入区域
        bottom = Label(self.Window, bg="#ABB2B9")
        bottom.place(relwidth=1, rely=0.825, relheight=0.175)

        self.entryMsg = Entry(bottom, bg="#2C3E50", fg="#EAECEE",
                              font="Helvetica 13")
        self.entryMsg.place(relwidth=0.74, relheight=0.06, relx=0.011)
        self.entryMsg.focus()

        Button(bottom, text="Send", bg="#ABB2B9", font="Helvetica 10 bold",
               command=lambda: self.sendButton(self.entryMsg.get())
               ).place(relx=0.77, rely=0.008, relheight=0.06, relwidth=0.22)

        # 群聊按钮
        Button(bottom, text="Group Chat", bg="#6C3483", fg="white",
               font="Helvetica 10 bold", command=self.group_chat
               ).place(relx=0.77, rely=0.08, relheight=0.05, relwidth=0.22)

        # AI Chat 独立窗口按钮
        Button(self.Window, text="AI Chat", bg="#2E86C1", fg="white",
               font="Helvetica 8 bold", command=self.open_ai_window
               ).place(relx=0.75, rely=0.02, relheight=0.05, relwidth=0.13)

        # 图像生成窗口按钮
        Button(self.Window, text="Image Gen", bg="#117A65", fg="white",
               font="Helvetica 8 bold", command=self.open_image_window
               ).place(relx=0.87, rely=0.02, relheight=0.05, relwidth=0.13)

    # 发送消息按钮逻辑
    def sendButton(self, msg):
        self.my_msg = msg
        self.entryMsg.delete(0, END)

    # 群聊
    def group_chat(self):
        self.send(json.dumps({"action": "connect", "target": "ALL"}))

    # ======================================================
    # AI Chat 独立窗口
    # ======================================================
    def open_ai_window(self):
        if hasattr(self, "ai_win") and self.ai_win.winfo_exists():
            self.ai_win.lift()
            return

        self.ai_win = Toplevel(self.Window)
        self.ai_win.title("Chat with TomAI")
        self.ai_win.geometry("520x560")
        self.ai_win.configure(bg="#1C2833")

        # 聊天显示区
        self.ai_text = Text(self.ai_win, bg="#17202A", fg="#EAECEE",
                            font="Helvetica 13", state=DISABLED)
        self.ai_text.pack(fill=BOTH, expand=True, padx=8, pady=(8, 0))

        # 人格选择
        frame = Frame(self.ai_win, bg="#1C2833")
        frame.pack(fill=X, padx=8, pady=6)

        Label(frame, text="AI Personality:", fg="white",
              bg="#1C2833", font="Helvetica 10 bold").pack(side=LEFT)

        self.persona_box = ttk.Combobox(
            frame,
            values=[
                "You are a friendly Python tutor.",
                "You are a strict professor who answers concisely.",
                "You are a humorous chatbot.",
                "You reply like a poem."
            ],
            state="readonly",
            font="Helvetica 10"
        )
        self.persona_box.set("You are a friendly Python tutor.")
        self.persona_box.pack(fill=X, expand=True, padx=6)

        # 输入框
        bottom = Frame(self.ai_win, bg="#1C2833")
        bottom.pack(fill=X, padx=8, pady=10)

        self.ai_entry = Entry(bottom, font="Helvetica 12",
                              bg="#2C3E50", fg="white")
        self.ai_entry.pack(side=LEFT, fill=X, expand=True)
        self.ai_entry.bind("<Return>", lambda e: self.ai_send_button())

        Button(bottom, text="Send", bg="#566573", fg="white",
               font="Helvetica 10 bold", command=self.ai_send_button
               ).pack(side=RIGHT)

    def _ai_append(self, msg):
        def append():
            self.ai_text.config(state=NORMAL)
            self.ai_text.insert(END, msg + "\n")
            self.ai_text.see(END)
            self.ai_text.config(state=DISABLED)
        self.ai_text.after(0, append)

    def ai_send_button(self):
        text = self.ai_entry.get().strip()
        if not text:
            return
        self.ai_entry.delete(0, END)

        persona = self.persona_box.get()

        self._ai_append(f"[You] {text}")

        self.send(json.dumps({
            "action": "ai_private_chat",
            "message": text,
            "persona": persona
        }))

    # ======================================================
    # 图片生成窗口
    # ======================================================
    def open_image_window(self):
        if hasattr(self, "img_win") and self.img_win.winfo_exists():
            self.img_win.lift()
            return

        self.img_win = Toplevel(self.Window)
        self.img_win.title("AI Image Generator")
        self.img_win.geometry("480x350")
        self.img_win.configure(bg="#1C2833")

        Label(self.img_win, text="Enter prompt:",
              fg="white", bg="#1C2833",
              font="Helvetica 12 bold").pack(pady=10)

        self.img_prompt = Entry(self.img_win, font="Helvetica 12",
                                bg="#2C3E50", fg="white", width=40)
        self.img_prompt.pack(pady=5)

        Button(self.img_win, text="Generate Image", font="Helvetica 11 bold",
               bg="#148F77", fg="white", command=self.generate_image
               ).pack(pady=12)

        self.img_status = Label(self.img_win, text="",
                                fg="#D5D8DC", bg="#1C2833",
                                font="Helvetica 10")
        self.img_status.pack(pady=10)

    def generate_image(self):
        prompt = self.img_prompt.get().strip()
        if not prompt:
            self.img_status.config(text="Please enter a prompt.")
            return

        self.img_status.config(text="Generating...")

        def worker():
            try:
                path = self.img_gen.generate(prompt)
                self.img_status.after(0,
                    lambda: self.img_status.config(text=f"Saved to: {path}"))
            except Exception as e:
                err = str(e)
                self.img_status.after(0, lambda err=err:
                                    self.img_status.config(text=f"Error: {err}"))


        threading.Thread(target=worker, daemon=True).start()

    # ======================================================
    # 后台消息处理线程
    # ======================================================
    def _recv_peer_msg(self):
        read, _, _ = select.select([self.socket], [], [], 0)
        if self.socket in read:
            try:
                raw = self.recv()
                return raw or ""
            except:
                return ""
        return ""

    def proc(self):
        """轮询服务器消息，并交给状态机处理"""
        while True:
            time.sleep(0.1)

            peer_msg = self._recv_peer_msg()

            # 状态机处理消息
            if self.my_msg or peer_msg:
                self.system_msg += self.sm.proc(self.my_msg, peer_msg)
                self.my_msg = ""

            # 显示在主窗口
            if self.system_msg:
                self.textCons.config(state=NORMAL)
                self.textCons.insert(END, self.system_msg)
                self.textCons.see(END)
                self.textCons.config(state=DISABLED)
                self.system_msg = ""

    def run(self):
        self.login()
        self.Window.mainloop()


# 启动（调试用）
if __name__ == "__main__":
    g = GUI()
