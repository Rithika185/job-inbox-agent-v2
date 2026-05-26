# JobInboxAgent v2

> Never miss an interview invite, offer, or rejection again.

An AI-powered web app that monitors your Gmail 24/7 and sends you an instant Telegram alert the moment an important job application email arrives — no keywords, pure semantic understanding.

---

## The Problem

When you apply to dozens of companies every day, your Gmail becomes a warzone:
- Auto-replies
- Job alert newsletters
- LinkedIn notifications
- Rejection emails
- The one interview invite that actually matters

They all look the same at first glance. And missing that one email can cost you an opportunity.

---

## The Solution

JobInboxAgent reads every incoming email using AI and understands the **intent** behind it:

| Category | Example |
|---|---|
| 🎉 Offer | "We'd like to extend you an offer..." |
| 🟢 Moving Forward | "We'd love to schedule a technical interview..." |
| 🔴 Rejected | "After careful consideration, we've decided..." |
| ⚪ Irrelevant | Newsletters, auto-replies, job alerts — silently ignored |

---

## How to Use (No Code Needed)

1. Visit the web app
2. Click **Connect with Google**
3. Set up your Telegram bot (see guide below)
4. Click **Start Monitoring**
5. Done — AI monitors your inbox every 5 minutes automatically

---

## Telegram Setup Guide

**Step 1 — Create your Telegram bot:**
1. Open Telegram → search **@BotFather**
2. Type `/newbot`
3. Give it a name → `JobInboxAgent`
4. Give it a username → `jobinboxagent_yourname_bot`
5. Copy the **bot token** BotFather gives you

**Step 2 — Get your Chat ID:**
1. Search your new bot in Telegram → tap **Start**
2. Send any message like `hello`
3. Open this URL in your browser (replace YOUR_TOKEN):
```
https://api.telegram.org/botYOUR_TOKEN/getUpdates
```
4. Find `"chat":{"id":` in the response → copy that number

**Step 3 — Enter on the website:**
- Paste your bot token → paste your chat ID → click **Start Monitoring!**

---

## Tech Stack

- **Python + Flask** — backend web framework
- **Gmail API + Google OAuth2** — secure Gmail access
- **Groq AI (LLaMA 3.3 70B)** — email intent classification
- **Few-shot Prompting** — AI learns from examples, no training needed
- **Telegram Bot API** — instant phone alerts
- **Railway** — 24/7 cloud hosting

---

## How the AI Works

This project uses **few-shot learning** — instead of training a model from scratch, the AI is given a few labeled examples of real job emails and generalizes from them.

No training data. No fine-tuning. No ML pipeline. Just 6 example emails and the AI figures out the rest.

It understands that these all mean the same thing:
- "We'd like to move forward"
- "Excited to continue the conversation"
- "Next steps in our hiring process"
- "Can you schedule a 30 minute call?"

---

## Run Locally (For Developers)

**1. Clone the repo:**
```bash
git clone https://github.com/Rithika185/jobinboxagent-v2.git
cd jobinboxagent-v2
```

**2. Install dependencies:**
```bash
pip install -r requirements.txt
```

**3. Set up Google OAuth:**
- Go to console.cloud.google.com
- Create a project → Enable Gmail API
- Create OAuth 2.0 credentials (Web Application)
- Add `http://localhost:5001/callback` to Authorized redirect URIs

**4. Get a Groq API key:**
- Go to console.groq.com → sign up free → create API key

**5. Create a `.env` file:**
```
GROQ_API_KEY=your_groq_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
REDIRECT_URI=http://localhost:5001/callback
FLASK_SECRET=any_random_string
```

**6. Run the app:**
```bash
OAUTHLIB_INSECURE_TRANSPORT=1 PORT=5001 python3 app.py
```

**7. Open in browser:**
```
http://localhost:5001
```

---

## Deploy on Railway

1. Fork this repo
2. Go to railway.app → New Project → Deploy from GitHub
3. Add environment variables in Railway dashboard:
```
GROQ_API_KEY=your_key
GOOGLE_CLIENT_ID=your_id
GOOGLE_CLIENT_SECRET=your_secret
FLASK_SECRET=any_random_string
REDIRECT_URI=https://your-railway-url/callback
```
4. Add your Railway URL to Google OAuth authorized redirect URIs
5. Done!

---

## Built By

**Rithika K S** — Machine Learning Engineer

Built this to solve my own problem of missing important job emails while actively applying.

- GitHub: [Rithika185](https://github.com/Rithika185)
- v1 CLI agent: [job-inbox-agent](https://github.com/Rithika185/job-inbox-agent)

---

## License

MIT — free to use, modify, and share.
