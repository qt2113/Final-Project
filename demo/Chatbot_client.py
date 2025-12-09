from ollama import Client
from openai import OpenAI
import copy

# ==============================================================================
# 1. Local Ollama Client 
# ==============================================================================
class ChatBotClient:
    def __init__(self, name="3po", model="gemma3", host='http://localhost:11434',
                  headers={'x-some-header': 'some-value'}):
        self.host = host
        self.name = name
        self.model = model
        self.client = Client(host=self.host, headers=headers)
        self.messages = []
    
    def chat(self, message: str):
        self.messages.append({"role": "user", "content": message})
        response = self.client.chat(self.model, messages=self.messages)
        msg = response["message"]["content"]
        self.messages.append({"role": "assistant", "content": msg})
        return msg

# ==============================================================================
# 2. Remote OpenAI Client 
# ==============================================================================
class ChatBotClientOpenAI:
    def __init__(self, name="AI", model="gemma2:2b", host="http://10.209.93.21:8000/v1"):
        self.client = OpenAI(api_key="EMPTY", base_url=host)
        self.model_id = model
        self.messages = []

    def chat(self, message: str):
        self.messages.append({"role": "user", "content": message})
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=self.messages,
                temperature=0.7,
                max_tokens=500
            )
            reply = response.choices[0].message.content.strip()
            self.messages.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            raise Exception(f"OpenAI Connection Error: {e}")

# ==============================================================================
# 3. Unified Client: Changes between Remote and Local
# ==============================================================================
class UnifiedChatClient:
    GLOBAL_BACKUP_MODE = False 

    def __init__(self, name="TomAI"):
        self.name = name
        self.primary = ChatBotClientOpenAI(name=name)       
        self.secondary = ChatBotClient(name=name, model='gemma3') 
        
    @property
    def messages(self):
        if UnifiedChatClient.GLOBAL_BACKUP_MODE:
            return self.secondary.messages
        return self.primary.messages

    @messages.setter
    def messages(self, value):
        self.primary.messages = copy.deepcopy(value)
        self.secondary.messages = copy.deepcopy(value)

    def chat(self, message: str):
        if UnifiedChatClient.GLOBAL_BACKUP_MODE:
            return self.secondary.chat(message)
        
        # try primary first
        try:
            return self.primary.chat(message)
        except Exception as e:
            print(f"\n[Warning] Remote AI Failed for {self.name}: {e}")
            print(f"[System] Global Failover Triggered. Switching ALL AI to Local LLM...\n")
            
            UnifiedChatClient.GLOBAL_BACKUP_MODE = True
            
            # sync history to secondary
            current_hist = self.primary.messages
            if current_hist and current_hist[-1].get('role') == 'user' and current_hist[-1].get('content') == message:
                sync_hist = current_hist[:-1]
            else:
                sync_hist = current_hist
            
            self.secondary.messages = copy.deepcopy(sync_hist)
            
            # finally use secondary
            return self.secondary.chat(message)