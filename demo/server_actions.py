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
            if sock is None: continue 
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
    
    if msg["message"].lower().strip() == "bye":
        print(f"{from_name} sent 'bye', disconnecting...")
        handle_disconnect(server, from_sock, msg)
        return
    
    the_guys = server.group.list_me(from_name)
    said = msg["from"] + msg["message"]
    
    # ============= AI Sentiment Analysis ============
    if from_name != "TomAI" and from_name != "[System]":  
        sentiment = server.sentiment_ai.get_sentiment(msg["message"])
    else:
        sentiment = None
    
    # ============ create message object ============
    msg_obj = {
        "from": from_name,
        "message": msg["message"],
        "sentiment": sentiment,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) 
    }

    # === save to group chat history ===
    # use sorted tuple of members as key
    sorted_key = tuple(sorted(the_guys))
    if sorted_key not in server.group_chat_history:
        server.group_chat_history[sorted_key] = []
    server.group_chat_history[sorted_key].append(msg_obj)

    found, group_key = server.group.find_group(from_name)
    if found:
        if group_key not in server.chat_history:
            server.chat_history[group_key] = []
        server.chat_history[group_key].append(msg_obj)

    # ===================== save to individual chat memory =====================
    if from_name not in server.chat_memory:
        server.chat_memory[from_name] = []
    server.chat_memory[from_name].append(msg_obj)
    
    said2 = text_proc(msg["message"], from_name)

    if from_name != "TomAI":
        server.indices[from_name].add_msg_and_index(said2)

    # ===== Broadcast to all peers in the group =====
    for g in the_guys:
        if g == from_name or g == "TomAI":
            continue  
        to_sock = server.logged_name2sock.get(g)
        if to_sock:
            # Send message with sentiment analysis result
            mysend(to_sock, json.dumps({
                "action": "exchange",
                "from": msg["from"],
                "message": msg["message"],
                "sentiment": sentiment
            }))
            if g in server.indices:
                server.indices[g].add_msg_and_index(said2)

def handle_list(server, from_sock, msg):
    from_name = server.logged_sock2name[from_sock]
    msg = server.group.list_all()
    mysend(from_sock, json.dumps({"action":"list", "results":msg}))

def handle_poem(server, from_sock, msg):
    pass 

def handle_time(server, from_sock, msg):
    ctime = time.strftime('%d.%m.%y,%H:%M', time.localtime())
    mysend(from_sock, json.dumps({"action":"time", "results":ctime}))

def handle_search(server, from_sock, msg):
    term = msg["target"]
    from_name = server.logged_sock2name[from_sock]
    print('search for ' + from_name + ' for ' + term)
    results = server.indices[from_name].search(term)
    search_rslt = '\n'.join([x[-1] for x in results]) if results else ""
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
    
    found, group_key = server.group.find_group(from_name)
    target_history = []
    
    if found:
        the_guys = server.group.list_me(from_name)
        sorted_key = tuple(sorted(the_guys))
        
        if sorted_key in server.group_chat_history:
            target_history = server.group_chat_history[sorted_key]
        elif group_key in server.chat_history:
            target_history = server.chat_history[group_key]
    
    # If no group history found, check individual chat memory
    if not target_history and from_name in server.chat_memory:
        target_history = server.chat_memory[from_name]

    if not target_history:
        summary = "No data available for summary."
    else:
        summary = server.summary_ai.summarize_chat(target_history)
        
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
        keywords = "No data available for keywords."
    else:
        keywords = server.keyword_ai.get_keywords(target_history)
        
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

    # 1. Ensure TomAI is in the group
    if "TomAI" not in members:
        members.append("TomAI")
        server.broadcast_to_peers(sender, json.dumps({
            "action": "exchange",
            "from": "[System]",
            "message": "TomAI has joined the chat.",
            "sentiment": None
        }))

    # 2. Broadcast the query message
    server.broadcast_to_peers(sender, json.dumps({
        "action": "exchange",
        "from": f"[{sender}]",
        "message": f"@TomAI {query}",
        "sentiment": "neutral"
    }))

    # 3. Get AI response (Calling the general chatbot instance)
    reply = server.call_remote_ai(query)
    
    # 4. Broadcast the AI response
    server.broadcast_to_peers(sender, json.dumps({
        "action": "exchange",
        "from": "[TomAI]",
        "message": reply,
        "sentiment": "neutral"
    }))

def handle_disconnect(server, from_sock, msg):
    if from_sock not in server.logged_sock2name:
        return
        
    from_name = server.logged_sock2name[from_sock]
    found, group_key = server.group.find_group(from_name)

    print(f"[Handle Disconnect] {from_name} is disconnecting...")

    # 1.If in a group, notify others and save history
    if found:
        the_guys = server.group.list_me(from_name)
        
        # Search for existing history
        history = []
        sorted_key = tuple(sorted(the_guys))
        if sorted_key in server.group_chat_history:
            history = server.group_chat_history[sorted_key]
        elif group_key in server.chat_history:
            history = server.chat_history[group_key]
        
        # send chat history to the disconnecting user
        mysend(from_sock, json.dumps({
            "action": "history",
            "results": history or []
        }))
        
        # broadcast to other members that this user is leaving
        for g in the_guys:
            if g == from_name or g == "TomAI":
                continue
            to_sock = server.logged_name2sock.get(g)
            if to_sock:
                mysend(to_sock, json.dumps({
                    "action": "exchange",
                    "from": f"[{from_name}]",
                    "message": f"{from_name} has left the chat.",
                    "sentiment": None 
                }))
        
        server.group.disconnect(from_name)

    # 2. send disconnect ack to the user
    try:
        mysend(from_sock, json.dumps({
            "action": "disconnect",
            "from": from_name
        }))
    except:
        pass