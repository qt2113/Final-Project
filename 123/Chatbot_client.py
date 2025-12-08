from ollama import Client
from openai import OpenAI


class ChatBotClient():

    def __init__(self, name="3po", model="gemma3", host='http://localhost:11434', headers={'x-some-header': 'some-value'}):
        self.host = host
        self.name = name
        self.model = model
        self.client = Client(host=self.host, headers=headers)
        # self.client = OpenAI(api_key="EMPTY", base_url="http://10.209.93.21:8000/v1")  # use this if switching to OpenAI-compatible API
        self.messages = []
    
    def chat(self, message: str):
        # If you want context, you can add previous conversation history
        self.messages.append({"role": "user", "content": message})

        response = self.client.chat(
            self.model,
            messages=self.messages
        )
        msg = response["message"]["content"]

        # Add assistant's response to the conversation context
        self.messages.append({"role": "assistant", "content": msg})
        return msg
    
    def stream_chat(self, message):
        self.messages.append({
            'role': 'user',
            'content': message,
        })
        response = self.client.chat(self.model, self.messages, stream=True)
        answer = ""
        for chunk in response:
            piece = chunk["message"]["content"]
            print(piece, end="")
            answer += piece
        self.messages.append({"role": "assistant", "content": answer})


class ChatBotClientOpenAI():
    def __init__(self, name="TomAI", host='http://10.209.93.21:8000/v1'):
        self.name = name
        self.host = host
        
        self.client = OpenAI(
            api_key="EMPTY",
            base_url=self.host
        )
        
        self.model_id = "/home/nlp/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/7ae557604adf67be50417f59c2c2f167def9a775"
        
        self.messages = [
            {"role": "system", "content": f"You are {name}, a friendly and patient Python programming teaching assistant. "
                                          "Use Chinese when user speaks Chinese, English otherwise. Be concise and helpful."}
        ]

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
            raise Exception(f"调用服务器失败: {e}")

    def stream_chat(self, message: str):
        self.messages.append({"role": "user", "content": message})
        stream = self.client.chat.completions.create(
            model=self.model_id,
            messages=self.messages,
            stream=True
        )
        answer = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                piece = chunk.choices[0].delta.content
                print(piece, end="", flush=True)
                answer += piece
        print()
        self.messages.append({"role": "assistant", "content": answer})
        return answer
    
if __name__ == "__main__":
    c = ChatBotClientOpenAI()
    print(c.chat("Your name is Tom, and you are the learning assistant of Python programming."))
    print(c.stream_chat("What's your name and role?"))