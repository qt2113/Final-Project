import socket
import sys
from chat_utils import *
import client_state_machine as csm
from GUI import *
from Chatbot_client import ChatBotClientOpenAI
from Chatbot_client import ChatBotClient
#你好

class Client:
    def __init__(self, args):
        self.args = args
        self.chatbot = ChatBotClientOpenAI(
                    name="TomAI",
                    host="http://10.209.93.21:8000/v1"   
                )
        #self.chatbot = ChatBotClient(name="TomAI", model='gemma3') 
        
    def quit(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def init_chat(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM )
        svr = SERVER if self.args.d == None else (self.args.d, CHAT_PORT)
        self.socket.connect(svr)
        self.sm = csm.ClientSM(self.socket)
        self.gui = GUI(self.send, self.recv, self.sm, self.socket, self.chatbot)

    def shutdown_chat(self):
        return

    def send(self, msg):
        mysend(self.socket, msg)

    def recv(self):
        return myrecv(self.socket)

    def run_chat(self):
        self.init_chat()
        self.gui.run()
        print("gui is off")
        self.quit()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Chat Client')
    parser.add_argument('-d', type=str, default=None, help='server IP addr')
    args = parser.parse_args()
    
    client = Client(args)
    client.run_chat()
