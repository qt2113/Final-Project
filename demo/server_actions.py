import json
from chat_utils import *
from chat_group import Group
import time

def handle_connect(server, from_sock, msg):
    to_name = msg["target"]
    from_name = server.logged_sock2name[from_sock]
    # =====connect to all=====
    if to_name == "ALL":
        print("Group chat requested by", from_name)
        server.group.connect_all()

        for user, sock in server.logged_name2sock.items():
            mysend(sock, json.dumps({
                "action": "connect",
                "status": "group-created",
                "from": from_name
            }))

        mysend(from_sock, json.dumps({
            "action": "connect",
            "status": "success"
        }))
        return
    # =====connect to one peer=====
    if to_name == from_name:
        msg = json.dumps({"action":"connect", "status":"server"})
    elif server.group.is_member(to_name):
        to_sock = server.logged_name2sock[to_name]
        server.group.connect(from_name, to_name)
        the_guys = server.group.list_me(from_name)
        msg = json.dumps({"action":"connect", "status":"success"})
        for g in the_guys[1:]:
            to_sock = server.logged_name2sock[g]
            mysend(to_sock, json.dumps({"action":"connect", "status":"request", "from":from_name}))
    else:
        msg = json.dumps({"action":"connect", "status":"no-user"})
    mysend(from_sock, msg)

def handle_exchange(server, from_sock, msg):
    from_name = server.logged_sock2name[from_sock]
    
    # ====== 特殊处理：检查是否是 bye 消息 ======
    if msg["message"].lower().strip() == "bye":
        print(f"{from_name} 发送了 bye，准备断开连接")
        # 复用 handle_disconnect 的逻辑来处理断开
        handle_disconnect(server, from_sock, msg)
        return
    
    # ====== 正常消息处理逻辑 ======
    the_guys = server.group.list_me(from_name)
    said = msg["from"]+msg["message"]
    
    # ============= AI Sentiment Analysis ============
    # 系统消息或机器人消息不分析情绪
    if from_name != "TomAI" and from_name != "[系统]":  
        sentiment = server.ai.get_sentiment(msg["message"])
    else:
        sentiment = None
    
    # ============ 生成消息对象 ==================
    msg_obj = {
        "from": from_name,
        "message": msg["message"],
        "sentiment": sentiment,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) 
    }

    # === 统一存储历史记录 ===
    # 使用排序的成员元组作为键，确保唯一性
    sorted_key = tuple(sorted(the_guys))
    if sorted_key not in server.group_chat_history:
        server.group_chat_history[sorted_key] = []
    server.group_chat_history[sorted_key].append(msg_obj)

    # === 兼容旧的 chat_history (以 group_key 为索引) ===
    found, group_key = server.group.find_group(from_name)
    if found:
        if group_key not in server.chat_history:
            server.chat_history[group_key] = []
        server.chat_history[group_key].append(msg_obj)

    # ===================== 保存到个人临时聊天存储器 =====================
    if from_name not in server.chat_memory:
        server.chat_memory[from_name] = []
    server.chat_memory[from_name].append(msg_obj)
    
    said2 = text_proc(msg["message"], from_name)

    # ===== AI 消息不写入索引 =====
    if from_name != "TomAI":
        server.indices[from_name].add_msg_and_index(said2)

    # ===== 向群组其他成员广播 =====
    for g in the_guys:
        if g == from_name or g == "TomAI":
            continue  # 发消息的人不重复发
        to_sock = server.logged_name2sock.get(g)
        if to_sock:
            # 发送消息并附加情绪
            mysend(to_sock, json.dumps({
                "action": "exchange",
                "from": msg["from"],
                "message": msg["message"],
                "sentiment": sentiment
            }))
            # 写入对方索引
            if g in server.indices:
                server.indices[g].add_msg_and_index(said2)

def handle_list(server, from_sock, msg):
    from_name = server.logged_sock2name[from_sock]
    msg = server.group.list_all()
    mysend(from_sock, json.dumps({"action":"list", "results":msg}))

def handle_poem(server, from_sock, msg):
    # 如果需要 sonnet 功能，确保 server 初始化了 sonnet
    # 这里保留原样
    pass 

def handle_time(server, from_sock, msg):
    ctime = time.strftime('%d.%m.%y,%H:%M', time.localtime())
    mysend(from_sock, json.dumps({"action":"time", "results":ctime}))

def handle_search(server, from_sock, msg):
    term = msg["target"]
    from_name = server.logged_sock2name[from_sock]
    print('search for ' + from_name + ' for ' + term)
    search_rslt = '\n'.join([x[-1] for x in server.indices[from_name].search(term)])
    print('server side search: ' + search_rslt)
    mysend(from_sock, json.dumps({"action":"search", "results":search_rslt}))

def handle_add(server, from_sock, msg):
    from_name = server.logged_sock2name[from_sock]
    target = msg["target"]

    if not server.group.is_member(target):
        mysend(from_sock, json.dumps({"action": "add", "status": "no-user"}))
        return

    found, group_key = server.group.find_group(from_name)
    if not found:
        server.group.connect(from_name, target)
        mysend(from_sock, json.dumps({"action": "add", "status": "created"}))
        return

    if target not in server.group.chat_grps[group_key]:
        server.group.chat_grps[group_key].append(target)

    for member in server.group.chat_grps[group_key]:
        if member != target:
            sock_m = server.logged_name2sock[member]
            mysend(sock_m, json.dumps({
                "action": "connect",
                "status": "success",
                "from": target
            }))

    to_sock = server.logged_name2sock[target]
    mysend(to_sock, json.dumps({
        "action": "connect",
        "status": "request",
        "from": from_name
    }))

def handle_summary(server, from_sock, msg):
    from_name = server.logged_sock2name[from_sock]
    print('Generating summary for ' + from_name)
    
    # 尝试找到用户所在的群组
    found, group_key = server.group.find_group(from_name)
    target_history = []
    
    if found:
        the_guys = server.group.list_me(from_name)
        sorted_key = tuple(sorted(the_guys))
        
        if sorted_key in server.group_chat_history:
            target_history = server.group_chat_history[sorted_key]
        elif group_key in server.chat_history:
            target_history = server.chat_history[group_key]
    
    # 退化：如果没群或没群记录，找个人记录
    if not target_history and from_name in server.chat_memory:
        target_history = server.chat_memory[from_name]

    if not target_history:
        summary = "当前没有聊天记录可供总结。"
    else:
        summary = server.ai.summarize_chat(target_history)
        
    mysend(from_sock, json.dumps({"action":"summary", "results":summary}))

def handle_keywords(server, from_sock, msg):
    from_name = server.logged_sock2name[from_sock]
    print('Generating keywords for ' + from_name)
    
    found, group_key = server.group.find_group(from_name)
    target_history = []
    
    if found:
        the_guys = server.group.list_me(from_name)
        sorted_key = tuple(sorted(the_guys))
        if sorted_key in server.group_chat_history:
            target_history = server.group_chat_history[sorted_key]
        elif group_key in server.chat_history:
            target_history = server.chat_history[group_key]
            
    if not target_history and from_name in server.chat_memory:
        target_history = server.chat_memory[from_name]

    if not target_history:
        keywords = "无数据"
    else:
        keywords = server.ai.get_keywords(target_history)
        
    mysend(from_sock, json.dumps({"action":"keywords", "results":keywords}))    

def handle_ai_query(server, from_sock, msg):
    sender = server.logged_sock2name[from_sock]
    query = msg["query"].strip()
    if not query:
        return

    in_group, gkey = server.group.find_group(sender)
    if not in_group:
        return

    members = server.group.chat_grps[gkey]

    # 1. 把 TomAI 拉进群（只进一次）
    if "TomAI" not in members:
        members.append("TomAI")
        server.broadcast_to_peers(sender, json.dumps({
            "action": "exchange",
            "from": "[系统]",
            "message": "TomAI 已被召唤进入群聊 ",
            "sentiment": None
        }))

    # 2. 广播用户的问题
    server.broadcast_to_peers(sender, json.dumps({
        "action": "exchange",
        "from": f"[{sender}]",
        "message": f"@TomAI {query}",
        "sentiment": "neutral"
    }))

    # 3. 调用 AI 并广播回答
    reply = server.call_remote_ai(query)
    
    # 这里的 remove_emoji 需要在 chat_utils 定义，如果没有定义建议注释掉
    # reply = remove_emoji(reply)

    server.broadcast_to_peers(sender, json.dumps({
        "action": "exchange",
        "from": "[TomAI]",
        "message": reply,
        "sentiment": "neutral"
    }))

# [修改] 完善后的 handle_disconnect，对齐 bye 的逻辑
def handle_disconnect(server, from_sock, msg):
    if from_sock not in server.logged_sock2name:
        return
        
    from_name = server.logged_sock2name[from_sock]
    found, group_key = server.group.find_group(from_name)

    print(f"[Handle Disconnect] {from_name} is disconnecting...")

    # 1. 如果在群组中，处理历史记录和通知
    if found:
        the_guys = server.group.list_me(from_name)
        
        # 查找历史记录 (优先尝试 sorted_key)
        history = []
        sorted_key = tuple(sorted(the_guys))
        if sorted_key in server.group_chat_history:
            history = server.group_chat_history[sorted_key]
        elif group_key in server.chat_history:
            history = server.chat_history[group_key]
        
        # 将历史记录发送给离开的用户 (保存记录)
        mysend(from_sock, json.dumps({
            "action": "history",
            "results": history or []
        }))
        
        # 通知其他群成员
        for g in the_guys:
            if g == from_name or g == "TomAI":
                continue
            to_sock = server.logged_name2sock.get(g)
            if to_sock:
                mysend(to_sock, json.dumps({
                    "action": "exchange",
                    "from": f"[{from_name}]",
                    "message": f"{from_name} 已离开聊天",
                    "sentiment": None # 系统通知不带情感
                }))
        
        # 执行群组断开逻辑
        server.group.disconnect(from_name)

    # 2. 发送最终的断开确认
    try:
        mysend(from_sock, json.dumps({
            "action": "disconnect",
            "from": from_name
        }))
    except:
        pass      