import subprocess
import time
import sys

# Find and kill processes on port 5000
result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
for line in result.stdout.splitlines():
    if ':5000' in line and 'LISTENING' in line:
        parts = line.split()
        pid = parts[-1]
        print(f"Killing PID {pid} on port 5000")
        subprocess.run(['taskkill', '/PID', pid, '/F'], capture_output=True)

time.sleep(2)

# Start the server
print("Starting server...")
subprocess.Popen([sys.executable, 'backend/main.py'], 
                 stdout=open('server_test.log', 'w'),
                 stderr=subprocess.STDOUT,
                 creationflags=subprocess.CREATE_NEW_CONSOLE)
print("Server started in background. Check server_test.log")