# 🚀 Setup Guide: Connecting ChatGPT to Antigravity

This guide walks you through setting up your own Custom GPT connected to your Antigravity agent bridge.

---

## Step 1: Start the Antigravity Bridge

You can run the bridge on your local machine or in a container.

### Local Development (with Tunnel)
```bash
# Clone the repository
git clone https://github.com/your-org/antigravity-chatgpt.git
cd antigravity-chatgpt

# Install dependencies
pip install -e .

# Launch bridge with automatic Cloudflare/ngrok tunnel
python tunnel/launch_tunnel.py
```
The script will display your public HTTPS tunnel URL, for example:
```
Tunnel URL: https://antigravity-bridge-abc.trycloudflare.com
```

---

## Step 2: Create a Custom GPT in ChatGPT

1. Open [ChatGPT](https://chatgpt.com/) and navigate to **Explore GPTs** -> **+ Create**.
2. Go to the **Configure** tab.
3. Fill in:
   * **Name**: `Antigravity Agent (Gemini BYOK)`
   * **Description**: `Autonomous coding, terminal debugging, and codebase refactoring powered by Google Antigravity and your personal Gemini API key.`
   * **Instructions**: Copy the prompt from [`chatgpt/gpt_instructions.md`](./gpt_instructions.md).

---

## Step 3: Add the Antigravity Action

1. In the GPT Builder Configure tab, scroll down to **Actions** and click **Create new action**.
2. Click **Import from URL** or paste the content of [`chatgpt/openapi.json`](./openapi.json).
3. If using a local tunnel or custom domain, update the `servers` URL to your public URL (e.g., `https://antigravity-bridge-abc.trycloudflare.com`).

---

## Step 4: Configure Authentication (BYOK Gemini API Key)

1. Under the Action settings, locate **Authentication**.
2. Select **API Key**.
3. Choose:
   * **Auth Type**: `Bearer` or `Custom` (`X-Gemini-API-Key`)
4. Obtain a Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey).
5. Paste your Gemini API Key into the API Key input field.
6. Save your Custom GPT (set access to **Only me** or **Anyone with a link**).

---

## Step 5: Test Your Agent!

Open a chat with your new Custom GPT and try:
> *"Test my Gemini API key and list available models."*

Then test code modification:
> *"Create a Python script that calculates prime numbers using the Sieve of Eratosthenes, write a pytest suite for it, and run the tests."*
