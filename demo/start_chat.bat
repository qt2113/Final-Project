@echo off
echo Starting Chat System...

:: 1. 启动服务器 (在新窗口中)
start "Chat Server" cmd /k "python chat_server.py"

:: 等待 1 秒确保服务器就绪
timeout /t 1 /nobreak >nul

:: 2. 启动第一个客户端 (Alice)
start "Client A" cmd /k "python chat_client_class.py"

:: 3. 启动第二个客户端 (Bob)
start "Client B" cmd /k "python chat_client_class.py"

:: 4. 启动第三个客户端 (test user)
start "Client C" cmd /k "python chat_client_class.py"

echo All systems running.