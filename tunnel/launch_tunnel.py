#!/usr/bin/env python3
"""
Quickstart script to launch the Antigravity ChatGPT bridge with an HTTPS tunnel.
Supports Cloudflare Quick Tunnels (no account needed) and ngrok.
"""

import os
import shutil
import subprocess
import sys
import time

def find_tunnel_tool():
    if shutil.which("cloudflared"):
        return "cloudflared"
    if shutil.which("ngrok"):
        return "ngrok"
    return None

def main():
    print("==================================================")
    print("🚀 Antigravity ChatGPT Bridge - Localhost Tunnel")
    print("==================================================")

    tool = find_tunnel_tool()
    port = os.getenv("PORT", "8000")

    if not tool:
        print("[!] Neither cloudflared nor ngrok was found in PATH.")
        print("[*] To expose your bridge to ChatGPT:")
        print("    Option 1: Install cloudflared (https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)")
        print("    Option 2: Install ngrok (https://ngrok.com/download)")
        print(f"[*] Starting local server on http://localhost:{port} only...\n")
        subprocess.run([sys.executable, "-m", "antigravity_chatgpt.app"])
        return

    print(f"[*] Detected tunnel tool: {tool}")
    print(f"[*] Starting bridge server on port {port}...")

    # Start FastAPI server in background
    server_proc = subprocess.Popen([sys.executable, "-m", "antigravity_chatgpt.app"])

    time.sleep(2)

    try:
        if tool == "cloudflared":
            print("[*] Starting Cloudflare Quick Tunnel...")
            subprocess.run(["cloudflared", "tunnel", "--url", f"http://localhost:{port}"])
        elif tool == "ngrok":
            print(f"[*] Starting ngrok on port {port}...")
            subprocess.run(["ngrok", "http", str(port)])
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
    finally:
        server_proc.terminate()
        server_proc.wait()

if __name__ == "__main__":
    main()
