"""
server_actions.py
服务器动作处理：每个 action 一个函数
"""

import json
import time
import threading
from chat_utils import *


# ============================================================
# 连接逻辑
# ============================================================
def handle_connect(server, from_sock, msg):
    to_name = msg["target"]
    from_name = server.logged_sock2name[from_sock]

    # ====== 群聊 ALL ======
    if to_name == "ALL":
        server.group.connect_all()

        # 通知所有在线用户
        for user, sock in server.logged_name2sock.items():
            mysend(sock, json.dumps({
                "action": "connect",
                "status": "group-created",
                "from": from_name
            }))

        # 给发起者确认
        mysend(from_sock, json.dumps({
            "action": "connect",
            "status": "success"
        }))
        return

    # ===== 单人私聊请求 =====
    if to_name == from_name:
        mysend(from_sock, json.dumps({
            "action": "connect",
            "status": "self"
        }))
        return

    if server.group.is_member(to_name):
        # 自动创建或加入两人 chat group
        server.group.connect(from_name, to_name)
        the_guys = server.group.list_me(from_name)

        mysend(from_sock, json.dumps({
            "action": "connect",
            "status": "success"
        }))

        # 发给对方“请求加入”
        for g in the_guys[1:]:
            sock = server.logged_name2sock[g]
            mysend(sock, json.dumps({
                "action": "connect",
                "status": "request",
                "from": from_name
            }))
    else:
        mysend(from_sock, json.dumps({
            "action": "connect",
            "status": "no-user"
        }))


# ============================================================
# 广播普通聊天消息（含情绪分析）
# ============================================================
def handle_exchange(server, from_sock, msg):
    from_name = server.logged_sock2name[from_sock]
    message = msg["message"]

    # 情绪分析
    try:
        sentiment = server.ai.analyze_sentiment(message)
    except:
        sentiment = "neutral"

    # 存历史
    the_guys = server.group.list_me(from_name)
    sorted_key = tuple(sorted(the_guys))

    msg_obj = {
        "from": from_name,
        "message": message,
        "sentiment": sentiment,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    }

    if sorted_key not in server.group_chat_history:
        server.group_chat_history[sorted_key] = []
    server.group_chat_history[sorted_key].append(msg_obj)

    # 广播
    server.broadcast_to_peers(from_name, json.dumps({
        "action": "exchange",
        "from": from_name,
        "message": message,
        "sentiment": sentiment
    }))


# ============================================================
# 在线列表
# ============================================================
def handle_list(server, from_sock, msg):
    lst = server.group.list_all()
    mysend(from_sock, json.dumps({"action": "list", "results": lst}))


# ============================================================
# 诗歌
# ============================================================
def handle_poem(server, from_sock, msg):
    idx = int(msg["target"])
    from_name = server.logged_sock2name[from_sock]

    poem = server.sonnet.get_poem(idx)
    poem = '\n'.join(poem).strip()

    mysend(from_sock, json.dumps({"action": "poem", "results": poem}))


# ============================================================
# 时间
# ============================================================
def handle_time(server, from_sock, msg):
    ctime = time.strftime('%d.%m.%y,%H:%M')
    mysend(from_sock, json.dumps({"action": "time", "results": ctime}))


# ============================================================
# 搜索
# ============================================================
def handle_search(server, from_sock, msg):
    term = msg["target"]
    from_name = server.logged_sock2name[from_sock]

    res = '\n'.join([x[-1] for x in server.indices[from_name].search(term)])
    mysend(from_sock, json.dumps({"action": "search", "results": res}))


# ============================================================
# add 成员进入聊天群
# ============================================================
def handle_add(server, from_sock, msg):
    from_name = server.logged_sock2name[from_sock]
    target = msg["target"]

    if not server.group.is_member(target):
        mysend(from_sock, json.dumps({"action": "add", "status": "no-user"}))
        return

    found, gkey = server.group.find_group(from_name)
    if not found:
        server.group.connect(from_name, target)
        mysend(from_sock, json.dumps({"action": "add", "status": "created"}))
        return

    # 加人到群
    if target not in server.group.chat_grps[gkey]:
        server.group.chat_grps[gkey].append(target)

    # 通知群成员
    for member in server.group.chat_grps[gkey]:
        if member != target:
            sock = server.logged_name2sock[member]
            mysend(sock, json.dumps({
                "action": "connect",
                "status": "success",
                "from": target
            }))

    # 给被加的人发送邀请
    t_sock = server.logged_name2sock[target]
    mysend(t_sock, json.dumps({
        "action": "connect",
        "status": "request",
        "from": from_name
    }))


# ============================================================
# AI 群聊问答（@TomAI）
# ============================================================
def handle_ai_query(server, from_sock, msg):
    sender = server.logged_sock2name[from_sock]
    query = msg["query"]

    # 广播问题
    server.broadcast_to_peers(sender, json.dumps({
        "action": "exchange",
        "from": f"[{sender}]",
        "message": f"@TomAI {query}",
        "sentiment": "neutral"
    }))

    # 异步调用 AI
    def worker():
        try:
            reply = server.ai.ask_llm(query)
        except Exception as e:
            reply = f"AI error: {e}"

        # 广播 AI 回复
        server.broadcast_to_peers(sender, json.dumps({
            "action": "exchange",
            "from": "[TomAI]",
            "message": reply,
            "sentiment": "neutral"
        }))

    threading.Thread(target=worker, daemon=True).start()


# ============================================================
# 私聊 AI，结果只回给一个人
# ============================================================
def handle_ai_private_chat(server, from_sock, msg):
    text = msg["message"]
    persona = msg["persona"]

    def worker():
        try:
            reply = server.ai.ask_llm(text, system_role=persona)
        except Exception as e:
            reply = f"[System error] {e}"

        mysend(from_sock, json.dumps({
            "action": "ai_private_chat_result",
            "results": reply
        }))

    threading.Thread(target=worker, daemon=True).start()


# ============================================================
# 断开连接
# ============================================================
def handle_disconnect(server, from_sock, msg):
    name = server.logged_sock2name[from_sock]

    found, gkey = server.group.find_group(name)

    # 离开前先取历史
    history = server.group_chat_history.get(gkey, []) if found else []

    server.group.disconnect(name)

    # 回给自己历史
    mysend(from_sock, json.dumps({
        "action": "history",
        "results": history
    }))

    # 通知其他人
    if found:
        server.broadcast_to_peers(name, json.dumps({
            "action": "disconnect",
            "from": name
        }))


# ============================================================
# 摘要
# ============================================================
def handle_summary(server, from_sock, msg):
    name = server.logged_sock2name[from_sock]
    the_guys = server.group.list_me(name)
    sorted_key = tuple(sorted(the_guys))

    history = server.group_chat_history.get(sorted_key, [])

    chat_text = "\n".join(
        f"{m['from']}: {m['message']}" for m in history[-50:]
    )

    def worker():
        try:
            result = server.ai.create_summary(chat_text)
        except:
            result = "Error."

        mysend(from_sock, json.dumps({
            "action": "summary_result",
            "results": result
        }))

    threading.Thread(target=worker, daemon=True).start()


# ============================================================
# 关键词
# ============================================================
def handle_keywords(server, from_sock, msg):
    name = server.logged_sock2name[from_sock]
    the_guys = server.group.list_me(name)
    sorted_key = tuple(sorted(the_guys))

    history = server.group_chat_history.get(sorted_key, [])

    chat_text = "\n".join(
        f"{m['from']}: {m['message']}" for m in history[-50:]
    )

    def worker():
        try:
            result = server.ai.extract_keywords(chat_text)
        except:
            result = "Error."

        mysend(from_sock, json.dumps({
            "action": "keywords_result",
            "results": result
        }))

    threading.Thread(target=worker, daemon=True).start()
