import threading
import select
from tkinter import *
from tkinter import messagebox, ttk
import json
import time
import hashlib
from chat_utils import * 
from image_generator import ImageGenerator

# ==== UI Styles ====
FONT_BOLD = "Helvetica 10 bold"
FONT_NORMAL = "Helvetica 12"
COLOR_BG_DARK = "#17202A"      
COLOR_BG_LIGHT = "#ABB2B9"     
COLOR_TEXT_WHITE = "#EAECEE"
COLOR_BTN_DEFAULT = "#ABB2B9"

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
        self.img_gen = ImageGenerator()
        self.name = ""

    def run(self):
        self.login()
        self.Window.mainloop()

    # =========================================================================
    # 1. Login logic and handling
    # =========================================================================
    def login(self):
        self.login_win = Toplevel()
        self.login_win.title("Login")
        self.login_win.resizable(False, False)
        self.login_win.geometry("400x300")
        
        Label(self.login_win, text="Please login to continue", justify=CENTER, 
              font="Helvetica 14 bold").place(relheight=0.15, relx=0.2, rely=0.07)
        
        Label(self.login_win, text="Name: ", font=FONT_NORMAL).place(relheight=0.2, relx=0.1, rely=0.2)
        self.entryName = Entry(self.login_win, font="Helvetica 14")
        self.entryName.place(relwidth=0.4, relheight=0.12, relx=0.35, rely=0.2)
        self.entryName.focus()

        Label(self.login_win, text="Password: ", font=FONT_NORMAL).place(relheight=0.2, relx=0.1, rely=0.35)
        self.entryPwd = Entry(self.login_win, font="Helvetica 14", show="*")
        self.entryPwd.place(relwidth=0.4, relheight=0.12, relx=0.35, rely=0.35)

        Button(self.login_win, text="CONTINUE", font="Helvetica 14 bold", 
               command=self.do_login).place(relx=0.4, rely=0.55)

    def do_login(self):
        name = self.entryName.get().strip()
        pwd = self.entryPwd.get()
        if not name or not pwd:
            return
        
        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
        msg = json.dumps({"action": "login", "name": name, "password": pwd_hash})
        try:
            self.send(msg)
        except Exception as e:
            messagebox.showerror("Network", f"Failed to send login: {e}")
            return

        threading.Thread(target=self._wait_login_response, args=(name,), daemon=True).start()

    def _wait_login_response(self, requested_name):
        try:
            raw = self.recv()
            if not raw: raise Exception("Empty response")
            response = json.loads(raw)
        except Exception as e:
            self.Window.after(0, lambda: messagebox.showerror("Login Error", str(e)))
            return

        status = response.get("status")
        if status == "ok":
            self.name = response.get("name", requested_name)
            self.Window.after(0, self._on_login_success)
        elif status == "wrong-password":
            self.Window.after(0, lambda: messagebox.showerror("Login Failed", "Wrong password."))
        elif status == "duplicate":
            self.Window.after(0, lambda: messagebox.showerror("Login Failed", "User already logged in."))

    def _on_login_success(self):
        if hasattr(self, "login_win"): self.login_win.destroy()
        self.sm.set_state(S_LOGGEDIN)
        self.sm.set_myname(self.name)
        
        self._setup_main_window()
        
        if not self.proc_thread or not self.proc_thread.is_alive():
            self.proc_thread = threading.Thread(target=self._proc_loop, daemon=True)
            self.proc_thread.start()

    # =========================================================================
    # 2. Main window layout
    # =========================================================================
    def _setup_main_window(self):
        self.Window.deiconify()
        self.Window.title("CHATROOM")
        self.Window.resizable(False, False)
        self.Window.configure(width=470, height=550, bg=COLOR_BG_DARK)

        # Upper name display
        Label(self.Window, text=self.name, bg=COLOR_BG_DARK, fg=COLOR_TEXT_WHITE,
              font="Helvetica 13 bold", pady=5).place(relwidth=1)
        Label(self.Window, width=450, bg=COLOR_BG_LIGHT).place(relwidth=1, rely=0.07, relheight=0.012)

        # Message display area
        self.textCons = Text(self.Window, width=20, height=2, bg=COLOR_BG_DARK, fg=COLOR_TEXT_WHITE,
                             font="Helvetica 14", padx=5, pady=5)
        self.textCons.place(relheight=0.745, relwidth=1, rely=0.08)
        
        self.textCons.config(state=NORMAL)
        try:
            self.textCons.insert(END, menu + "\n\n")
        except NameError:
            self.textCons.insert(END, "Welcome to Chatroom!\n\n")
        self.textCons.config(state=DISABLED)
        
        scrollbar = Scrollbar(self.textCons)
        scrollbar.place(relheight=1, relx=0.974)
        scrollbar.config(command=self.textCons.yview)

        # 底部操作区
        self.labelBottom = Label(self.Window, bg=COLOR_BG_LIGHT, height=80)
        self.labelBottom.place(relwidth=1, rely=0.825)

        self.entryMsg = Entry(self.labelBottom, bg="#2C3E50", fg=COLOR_TEXT_WHITE, font="Helvetica 13")
        self.entryMsg.place(relwidth=0.74, relheight=0.06, rely=0.008, relx=0.011)
        self.entryMsg.focus()
        self.entryMsg.bind("<Return>", lambda x: self.send_message())

        # ==== 按钮区域 ====
        # Send Button
        self._create_btn(self.labelBottom, "Send", self.send_message, 
                         bg=COLOR_BTN_DEFAULT, x=0.77, y=0.008, w=0.22, h=0.06)
        
        
        self._create_btn(self.labelBottom, "Group Chat", lambda: self.send_command("connect", "ALL"),
                         bg="#6C3483", fg="white", x=0.77, y=0.08, w=0.22, h=0.05)

        # Summary 
        self._create_btn(self.labelBottom, "Summary", lambda: self.send_text_command("/summary"),
                         bg="#D35400", fg="white", font="Helvetica 9 bold", x=0.77, y=0.15, w=0.10, h=0.05)

        # Keywords 
        self._create_btn(self.labelBottom, "Keywords", lambda: self.send_text_command("/keywords"),
                         bg="#27AE60", fg="white", font="Helvetica 9 bold", x=0.89, y=0.15, w=0.10, h=0.05)

        # AI Chat 
        self._create_btn(self.Window, "AI Chat", self._open_ai_window,
                         bg="#2E86C1", fg="white", font="Helvetica 8 bold", x=0.75, y=0.02, w=0.13, h=0.05)
        
        # Image Gen 
        self._create_btn(self.Window, "Image Gen", self._open_image_window,
                         bg="#117A65", fg="white", font="Helvetica 8 bold", x=0.87, y=0.02, w=0.13, h=0.05)

    def _create_btn(self, parent, text, cmd, bg="gray", fg="black", font=FONT_BOLD, x=0, y=0, w=0.1, h=0.05):
        btn = Button(parent, text=text, font=font, bg=bg, fg=fg, command=cmd)
        btn.place(relx=x, rely=y, relwidth=w, relheight=h)
        return btn

    # =========================================================================
    # 3. Message sending and receiving
    # =========================================================================
    def send_message(self):
        msg = self.entryMsg.get()
        if msg:
            self.my_msg = msg
            self.entryMsg.delete(0, END)

    def send_command(self, action, target):
        self.send(json.dumps({"action": action, "target": target}))

    def send_text_command(self, text):
        self.my_msg = text

    def _recv_peer_msg(self):
        read, _, _ = select.select([self.socket], [], [], 0)
        if self.socket in read:
            try:
                raw = self.recv()
                return raw if raw else ""
            except:
                return ""
        return ""

    def _proc_loop(self):
        while True:
            time.sleep(0.1)
            peer_msg = self._recv_peer_msg()
            
            if self.my_msg or peer_msg:
                self.system_msg += self.sm.proc(self.my_msg, peer_msg)
                self.my_msg = ""
            
            if self.system_msg:
                self.textCons.config(state=NORMAL)
                self.textCons.insert(END, self.system_msg)
                self.textCons.config(state=DISABLED)
                self.textCons.see(END)
                self.system_msg = ""

    # =========================================================================
    # 4. Sub windows: AI Chat and Image Generation
    # =========================================================================
    def _open_ai_window(self):
        if hasattr(self, "ai_win") and self.ai_win.winfo_exists():
            self.ai_win.lift()
            return

        self.ai_win = Toplevel(self.Window)
        self.ai_win.title("Chat with TomAI")
        self.ai_win.geometry("520x560")
        self.ai_win.configure(bg="#1C2833")

        self.ai_text = Text(self.ai_win, state=DISABLED, wrap=WORD, bg="#17202A", fg="#EAECEE", font="Helvetica 13")
        self.ai_text.pack(fill=BOTH, expand=True, padx=8, pady=8)

        frame = Frame(self.ai_win, bg="#1C2833")
        frame.pack(fill=X, padx=8, pady=5)
        Label(frame, text="Personality:", fg="white", bg="#1C2833").pack(side=LEFT)
        self.persona_box = ttk.Combobox(frame, values=[
            "You are a friendly Python tutor.",
            "You are a strict professor.",
            "You are a humorous chatbot.",
            "You are a poetic assistant."
        ], state="readonly")
        self.persona_box.set("You are a friendly Python tutor.")
        self.persona_box.pack(side=LEFT, fill=X, expand=True, padx=5)

        bottom = Frame(self.ai_win, bg="#1C2833")
        bottom.pack(fill=X, padx=8, pady=10)
        self.ai_entry = Entry(bottom, font="Helvetica 12", bg="#2C3E50", fg="white")
        self.ai_entry.pack(side=LEFT, fill=X, expand=True)
        self.ai_entry.bind("<Return>", lambda e: self._ai_send())
        Button(bottom, text="Send", command=self._ai_send, bg="#566573", fg="white").pack(side=RIGHT, padx=5)

    def _ai_send(self):
        text = self.ai_entry.get().strip()
        if not text: return
        self.ai_entry.delete(0, END)
        
        self._append_ai_text(f"[You] {text}")
        threading.Thread(target=self._ai_thread_task, args=(text,), daemon=True).start()

    def _ai_thread_task(self, text):
        try:
            self.chatbot.messages = [{"role": "system", "content": self.persona_box.get()}]
            reply = self.chatbot.chat(text)
            self.ai_win.after(0, lambda: self._append_ai_text(f"[TomAI] {reply}"))
        except Exception as e:
            self.ai_win.after(0, lambda: self._append_ai_text(f"[Error] {e}"))

    def _append_ai_text(self, msg):
        if not hasattr(self, "ai_text"): return
        self.ai_text.config(state=NORMAL)
        self.ai_text.insert(END, msg + "\n")
        self.ai_text.see(END)
        self.ai_text.config(state=DISABLED)

    def _open_image_window(self):
        if hasattr(self, "img_win") and self.img_win.winfo_exists():
            self.img_win.lift()
            return
            
        self.img_win = Toplevel(self.Window)
        self.img_win.title("AI Image Generator")
        self.img_win.geometry("480x250")
        self.img_win.configure(bg="#1C2833")

        Label(self.img_win, text="Enter prompt:", font="Helvetica 12 bold", bg="#1C2833", fg="white").pack(pady=10)
        self.img_prompt = Entry(self.img_win, font="Helvetica 12", width=40)
        self.img_prompt.pack(pady=5)
        
        self.img_status = Label(self.img_win, text="", bg="#1C2833", fg="#D5D8DC")
        self.img_status.pack(pady=10)
        
        Button(self.img_win, text="Generate", font="Helvetica 11 bold", bg="#148F77", fg="white",
               command=self._generate_image_task).pack(pady=5)

    def _generate_image_task(self):
        prompt = self.img_prompt.get().strip()
        if not prompt: return
        self.img_status.config(text="Generating...")
        
        def worker():
            try:
                path = self.img_gen.generate(prompt, save_path="generated_image.png")
                self.img_status.after(0, lambda: self.img_status.config(text=f"Saved to: {path}"))
            except Exception as e:
                self.img_status.after(0, lambda: self.img_status.config(text=f"Error: {e}"))
        
        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    g = GUI(None, None, None, None, None)
    g.run()