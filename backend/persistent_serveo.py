import subprocess
import time
import sys

print("Starting SSH Serveo worker...")
proc = subprocess.Popen(
    ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-R", "80:127.0.0.1:8000", "serveo.net"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

# Keep alive loop
while True:
    try:
        # Check if process is still alive
        if proc.poll() is not None:
            print("SSH disconnected, restarting...")
            proc = subprocess.Popen(
                ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-R", "80:127.0.0.1:8000", "serveo.net"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            time.sleep(5)
            
        line = proc.stdout.readline()
        if line:
            print(f"[TUNNEL] {line.strip()}", flush=True)
            
        # Small read for stderr
        err = proc.stderr.readline()
        if err:
            print(f"[ERR] {err.strip()}", flush=True)
            
    except Exception as e:
        print(f"Error in tunnel loop: {e}", flush=True)
        time.sleep(2)
