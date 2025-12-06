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

# def handle_exchange(server,from_sock, msg):
#     from_name = server.logged_sock2name[from_sock]
#     the_guys = server.group.list_me(from_name)
#     said = msg["from"]+msg["message"]
#     #=============AI Sentiment Analysis ============
#     if from_name != "TomAI":               
#         sentiment = server.ai.get_sentiment(msg["message"])
#     else:
#         sentiment = None
#     # ============ 生成消息对象 ==================
#     msg_obj = {
#         "from": from_name,
#         "message": msg["message"],
#         "sentiment": sentiment,
#         "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) 
#     }

#     # === 同时保存到两种历史记录中确保一致性 ===
#     # 方式1：使用成员排序元组作为键（与disconnect保持一致）
#     sorted_key = tuple(sorted(the_guys))
#     if sorted_key not in server.group_chat_history:
#         server.group_chat_history[sorted_key] = []
#     server.group_chat_history[sorted_key].append(msg_obj)

#     # === 保存到群聊历史 ===
#     found, group_key = server.group.find_group(from_name)
#     if found:
#         if group_key not in server.chat_history:   # 新建群历史
#             server.chat_history[group_key] = []
#         server.chat_history[group_key].append(msg_obj)

#     # ===================== 新增：保存到临时聊天存储器 =====================
#     if from_name not in server.chat_memory:
#         server.chat_memory[from_name] = []
#     server.chat_memory[from_name].append(msg_obj)
#     said2 = text_proc(msg["message"], from_name)

#     # ===== 1. AI 不写入聊天记录 =====
#     if from_name != "TomAI":
#         server.indices[from_name].add_msg_and_index(said2)

#     # # ======== 保存完整群聊记录 ========
#     # # 把一个群视为成员组成的 tuple key，使其可作为字典键
#     # group_key = tuple(sorted(the_guys))

#     # if group_key not in server.group_chat_history:
#     #     server.group_chat_history[group_key] = []


#     # # 保存记录（包含 emoji 情绪标签）
#     # server.group_chat_history[group_key].append({
#     #     "from": from_name,
#     #     "message": msg["message"],
#     #     "sentiment": sentiment,
#     #     "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
#     # })

#     # ===== 2. 向群组其他成员广播 =====
#     for g in the_guys:
#         if g == from_name or g == "TomAI":
#             continue  # 发消息的人不重复写
#         to_sock = server.logged_name2sock[g]
#         # 发送消息并附加情绪
#         mysend(to_sock, json.dumps({
#             "action": "exchange",
#             "from": msg["from"],
#             "message": msg["message"],
#             "sentiment": sentiment
#         }))
#         # 写入对方索引
#         if g in server.indices:
#             server.indices[g].add_msg_and_index(said2)
    
def handle_exchange(server, from_sock, msg):
    from_name = server.logged_sock2name[from_sock]
    
    # ====== 第一步：检查是否是 bye 消息 ======
    if msg["message"].lower().strip() == "bye":
        print(f"{from_name} 发送了 bye，准备断开连接")
        
        # 获取群组信息
        found, group_key = server.group.find_group(from_name)
        
        if found:
            # 1. 获取当前群聊的所有成员
            the_guys = server.group.list_me(from_name)
            print(f"群聊成员: {the_guys}")
            
            # 2. 获取完整的群聊历史记录
            history = []
            
            # 首先尝试从 group_chat_history 获取（使用排序元组作为键）
            sorted_key = tuple(sorted(the_guys))
            print(f"查找历史记录键: {sorted_key}")
            
            if sorted_key in server.group_chat_history:
                history = server.group_chat_history[sorted_key][:]  # 获取副本
                print(f"从 group_chat_history 找到 {len(history)} 条记录")
            else:
                # 如果上面没找到，尝试从 chat_history 获取
                print(f"尝试从 chat_history[group_key={group_key}] 查找...")
                if group_key in server.chat_history:
                    history = server.chat_history[group_key][:]  # 获取副本
                    print(f"从 chat_history 找到 {len(history)} 条记录")
                else:
                    # 两种方式都没找到，打印调试信息
                    print(f"调试信息 - group_chat_history 键: {list(server.group_chat_history.keys())}")
                    print(f"调试信息 - chat_history 键: {list(server.chat_history.keys())}")
            
            # 3. 发送历史记录给发送者
            if history:
                mysend(from_sock, json.dumps({
                    "action": "history",
                    "results": history
                }))
                print(f"向 {from_name} 发送了历史记录，共 {len(history)} 条")
            else:
                print(f"没有找到 {from_name} 的历史记录")
                # 即使没有历史记录，也发送空的历史响应
                mysend(from_sock, json.dumps({
                    "action": "history",
                    "results": []
                }))
            
            # 4. 通知其他成员有人离开（系统消息，不显示emoji）
            for g in the_guys:
                if g == from_name or g == "TomAI":
                    continue
                to_sock = server.logged_name2sock.get(g)
                if to_sock:
                    mysend(to_sock, json.dumps({
                        "action": "exchange",
                        "from": f"[{from_name}]",
                        "message": f"{from_name} 已离开聊天",
                        "sentiment": None  # 系统消息，不显示emoji
                    }))
            
            # 5. 执行断开连接
            server.group.disconnect(from_name)
            
            # 6. 不要立即清除历史记录，等确认发送后再清除
            # 先注释掉清除代码，确保能获取到历史记录
            # if sorted_key in server.group_chat_history:
            #     del server.group_chat_history[sorted_key]
            # if group_key in server.chat_history:
            #     del server.chat_history[group_key]
            
            print(f"{from_name} 已断开连接")
        
        # 7. 发送最终的断开确认
        mysend(from_sock, json.dumps({
            "action": "disconnect",
            "from": from_name
        }))
        
        return  # 直接返回，不处理后续的消息广播逻辑
    
    # ====== 原来的正常消息处理逻辑 ======
    the_guys = server.group.list_me(from_name)
    said = msg["from"]+msg["message"]
    
    #=============AI Sentiment Analysis ============
    if from_name != "TomAI" and from_name != "[系统]":  # 系统消息不分析情绪               
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
    # 主要使用排序的成员元组作为键
    sorted_key = tuple(sorted(the_guys))
    if sorted_key not in server.group_chat_history:
        server.group_chat_history[sorted_key] = []
    server.group_chat_history[sorted_key].append(msg_obj)

    # === 同时保存到 chat_history 用于兼容 ===
    found, group_key = server.group.find_group(from_name)
    if found:
        if group_key not in server.chat_history:
            server.chat_history[group_key] = []
        server.chat_history[group_key].append(msg_obj)

    # ===================== 保存到临时聊天存储器 =====================
    if from_name not in server.chat_memory:
        server.chat_memory[from_name] = []
    server.chat_memory[from_name].append(msg_obj)
    said2 = text_proc(msg["message"], from_name)

    # ===== AI 不写入聊天记录 =====
    if from_name != "TomAI":
        server.indices[from_name].add_msg_and_index(said2)

    # ===== 向群组其他成员广播 =====
    for g in the_guys:
        if g == from_name or g == "TomAI":
            continue  # 发消息的人不重复写
        to_sock = server.logged_name2sock[g]
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
    poem_indx = int(msg["target"])
    from_name = server.logged_sock2name[from_sock]
    print(from_name + ' asks for ', poem_indx)
    poem = server.sonnet.get_poem(poem_indx)
    poem = '\n'.join(poem).strip()
    print('here:\n', poem)
    mysend(from_sock, json.dumps({"action":"poem", "results":poem}))

def handle_time(server, from_sock, msg):
    ctime = time.strftime('%d.%m.%y,%H:%M', time.localtime())
    mysend(from_sock, json.dumps({"action":"time", "results":ctime}))

def handle_search(server, from_sock, msg):
    term = msg["target"]
    from_name = server.logged_sock2name[from_sock]
    print('search for ' + from_name + ' for ' + term)
    # search_rslt = (server.indices[from_name].search(term))
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
    
# def handle_ai_query(server, from_sock, msg):
#     from_name = server.logged_sock2name[from_sock]
#     query = msg["query"]

#     # ===== 关键：自动把 TomAI 拉进当前群聊（只拉一次）=====
#     in_group, group_key = server.group.find_group(from_name)
#     if in_group and "TomAI" not in server.group.chat_grps[group_key]:
#         server.group.chat_grps[group_key].append("TomAI")
#         print(f"TomAI 已被 {from_name} 召唤进入群聊")
#         for member in server.group.chat_grps[group_key]:
#             if member != "TomAI" and server.logged_name2sock[member] is not None:
#                 mysend(server.logged_name2sock[member], json.dumps({
#                     "action": "connect",
#                     "status": "success",      
#                     "from": "TomAI"           
#                 }))

#     # 调用 AI
#     reply = server.call_remote_ai(query)
#     reply = remove_emoji(reply)    
#     # 广播给当前群聊的所有人（包括提问者自己）
#     the_guys = server.group.list_me(from_name)  # 包含 TomAI
#     for g in the_guys:
#         if g == "TomAI":
#             continue  # 机器人自己不需要收到消息
#         to_sock = server.logged_name2sock[g]
#         mysend(to_sock, json.dumps({
#             "action": "exchange",
#             "from": "[TomAI]",
#             "message": reply
#         }))

def handle_ai_query(server, from_sock, msg):
    sender = server.logged_sock2name[from_sock]
    query = msg["query"].strip()
    if not query:
        return

    # 找到当前群聊
    in_group, gkey = server.group.find_group(sender)
    if not in_group:
        return

    members = server.group.chat_grps[gkey]

    # 1. 把 TomAI 拉进群（只进一次）
    if "TomAI" not in members:
        members.append("TomAI")
        # 可选：提示大家 TomAI 来了
        server.broadcast_to_peers(sender, json.dumps({
            "action": "exchange",
            "from": "[系统]",
            "message": "TomAI 已被召唤进入群聊 ",
            "sentiment": None
        }))

    # 2. 广播用户的问题（关键！）
    server.broadcast_to_peers(sender, json.dumps({
        "action": "exchange",
        "from": f"[{sender}]",
        "message": f"@TomAI {query}",
        "sentiment": "neutral"
    }))

    # 3. 调用 AI 并广播回答
    reply = server.call_remote_ai(query)
    reply = remove_emoji(reply)

    server.broadcast_to_peers(sender, json.dumps({
        "action": "exchange",
        "from": "[TomAI]",
        "message": reply,
        "sentiment": "neutral"
    }))

def handle_disconnect(server, from_sock, msg):
    # from_name = server.logged_sock2name[from_sock]
    # the_guys = server.group.list_me(from_name)

    # # 首先获取群组信息
    # found, actual_group_key = server.group.find_group(from_name)

    # # ===== 获取群聊历史记录 =====
    # # 尝试从两种方式获取历史记录
    # history = []

    # # 方式1：使用成员排序元组作为键
    # sorted_key = tuple(sorted(the_guys))
    # if sorted_key in server.group_chat_history:
    #     history = server.group_chat_history[sorted_key]
    
    # # 方式2：如果方式1没有，则使用group.find_group返回的键
    # if not history and found and actual_group_key in server.chat_history:
    #     history = server.chat_history.get(actual_group_key, [])
    
    # # # 修复：直接使用 the_guys 创建 group_key，不重复添加 from_name
    # # group_key = tuple(sorted(the_guys))
    # # history = server.group_chat_history.get(group_key, [])
    
    # # # 如果没有找到历史记录，尝试从 chat_history 中查找
    # # if not history:
    # #     found, actual_group_key = server.group.find_group(from_name)
    # #     if found:
    # #         # 从 chat_history 获取历史记录
    # #         history = server.chat_history.get(actual_group_key, [])
    
    # # ===== 返回记录给退出者 =====
    # mysend(from_sock, json.dumps({
    #     "action": "history",
    #     "results": history  # list
    # }))
    
    # # 清除该群聊的历史记录（可选）
    # if sorted_key in server.group_chat_history:
    #     del server.group_chat_history[sorted_key]
    
    # if found and actual_group_key in server.chat_history:
    #     del server.chat_history[actual_group_key]
    
    # server.group.disconnect(from_name)
    # the_guys.remove(from_name)
    # if len(the_guys) == 1:  # only one left
    #     g = the_guys.pop()
    #     to_sock = server.logged_name2sock[g]
    #     mysend(to_sock, json.dumps({"action":"disconnect"}))
    name = server.logged_sock2name[from_sock]
    in_group, gkey = server.group.find_group(name)

    # 断开前先记住历史（如果有群）
    history = server.group_chat_history.get(gkey, []) if in_group else []

    # 执行断开（会自动解散只剩1人的群）
    server.group.disconnect(name)

    # 把历史发给离开的人
    if history:
        mysend(from_sock, json.dumps({"action": "history", "results": history}))

    # 通知其他人有人离开（可选）
    if in_group:
        server.broadcast_to_peers(name, json.dumps({
            "action": "disconnect",
            "from": name
        }))
                