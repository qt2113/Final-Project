import socket
import threading
from Chat_System_Basic.simple_gui.chat_bot_client import ChatBotClientOpenAI


class ChatBotManager:
    def __init__(self):
        self.bot = ChatBotClientOpenAI()
        self.personality = "normal"
        self.history = []  # 记录上下文对话

    def set_personality(self, style):
        self.personality = style

    def build_prompt(self):
        personality_map = {
            "normal": "You are a friendly assistant.",
            "funny": "You are a funny bot, always joke around.",
            "tsundere": "You are a tsundere anime character, a little rude but cute.",
            "academic": "You answer like a professional academic scholar with serious tone."
        }
        return personality_map.get(self.personality, personality_map["normal"])

    def chat(self, user_msg):
        system_prompt = self.build_prompt()
        self.history.append({"role": "user", "content": user_msg})
        reply = self.bot.chat(history=self.history, system_prompt=system_prompt)
        self.history.append({"role": "assistant", "content": reply})
        return reply
    

HOST = '127.0.0.1'
PORT = 5555
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

clients = []
bot_manager = ChatBotManager()  # 创建唯一的机器人

def broadcast(message):
    for client in clients:
        try:
            client.send(message.encode())
        except:
            pass

def handle_client(conn, addr):
    conn.send("欢迎加入聊天系统！\n".encode())
    while True:
        try:
            msg = conn.recv(1024).decode().strip()

            # -------- 设置机器人性格 --------
            if msg.startswith("/set personality"):
                style = msg.split()[-1]
                bot_manager.set_personality(style)
                broadcast(f"[系统] 机器人性格已设置为：{style}")
                continue

            broadcast(msg)  # 广播给所有用户

            # -------- 触发机器人回复：必须 @bot --------
            if "@bot" in msg:
                user_text = msg.replace("@bot", "").strip()
                reply = bot_manager.chat(user_text)
                broadcast(f"[Bot]: {reply}")

        except:
            clients.remove(conn)
            conn.close()
            break

def receive():
    while True:
        conn, addr = server.accept()
        clients.append(conn)
        threading.Thread(target=handle_client, args=(conn, addr)).start()

print("服务器启动中...")
receive()



print("服务器已启动，输入 @bot + 内容 与 AI 对话！\n")

while True:
    user_input = input("你: ")

    # 如果用户输入 @bot 开头，转给 AI
    if user_input.startswith("@bot"):
        message = user_input.replace("@bot", "", 1).strip()
        reply = bot_manager.chat(message)
        print("🤖 机器人:", reply)

    # 普通消息仅打印，不给机器人
    else:
        print("（其他用户消息，不触发机器人）")