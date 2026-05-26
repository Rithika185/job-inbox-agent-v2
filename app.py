import os
import threading
import time
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, session, redirect, request, render_template, url_for
import google.oauth2.credentials
import google.oauth2.id_token
import google_auth_oauthlib.flow
import googleapiclient.discovery
import google.auth.transport.requests
from groq import Groq

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "jobinboxagent2025")

GROQ_API_KEY  = os.environ.get("GROQ_API_KEY", "")
CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI  = os.environ.get("REDIRECT_URI", "http://localhost:5001/callback")

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

active_agents = {}

EXAMPLES = """
EXAMPLE 1 - MOVING_FORWARD:
Email: "We would love for you to complete a technical assessment."
Label: MOVING_FORWARD | Invited to complete assessment

EXAMPLE 2 - REJECTED:
Email: "After careful consideration, we have decided to move forward with other candidates."
Label: REJECTED | Company pursuing other candidates

EXAMPLE 3 - OFFER:
Email: "Congratulations! We are thrilled to extend you an offer."
Label: OFFER | Job offer extended

EXAMPLE 4 - MOVING_FORWARD:
Email: "Could you schedule a 30 minute call with our hiring manager?"
Label: MOVING_FORWARD | Interview call requested

EXAMPLE 5 - REJECTED:
Email: "We regret to inform you that we will not be moving forward."
Label: REJECTED | Application rejected

EXAMPLE 6 - IRRELEVANT:
Email: "50 new Machine Learning jobs in your area."
Label: IRRELEVANT | Job alert newsletter

EXAMPLE 7 - IRRELEVANT:
Email: "Thank you for applying. We will contact you if there is a good match."
Label: IRRELEVANT | Auto-reply, not a real decision

EXAMPLE 8 - IRRELEVANT:
Email: "We received your application and will be in touch."
Label: IRRELEVANT | Automated acknowledgment
"""

CLIENT_CONFIG = {
    "web": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [REDIRECT_URI],
    }
}

def make_flow():
    return google_auth_oauthlib.flow.Flow.from_client_config(
        CLIENT_CONFIG, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )

def get_gmail_service(creds_data):
    creds = google.oauth2.credentials.Credentials(
        token=creds_data["token"],
        refresh_token=creds_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(google.auth.transport.requests.Request())
        creds_data["token"] = creds.token
    return googleapiclient.discovery.build("gmail", "v1", credentials=creds)

def get_unread_emails(service):
    res = service.users().messages().list(
        userId="me", labelIds=["INBOX", "UNREAD"], maxResults=10
    ).execute()
    emails = []
    for msg in res.get("messages", []):
        full = service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()
        hdrs = full["payload"]["headers"]
        subject = next((h["value"] for h in hdrs if h["name"] == "Subject"), "")
        sender  = next((h["value"] for h in hdrs if h["name"] == "From"), "")
        body = ""
        pl = full["payload"]
        if "parts" in pl:
            for p in pl["parts"]:
                if p["mimeType"] == "text/plain":
                    d = p["body"].get("data", "")
                    if d:
                        body = base64.urlsafe_b64decode(d).decode("utf-8", errors="ignore")
                        break
        elif "body" in pl:
            d = pl["body"].get("data", "")
            if d:
                body = base64.urlsafe_b64decode(d).decode("utf-8", errors="ignore")
        emails.append({"id": msg["id"], "subject": subject, "sender": sender, "body": body[:800]})
    return emails

def classify_email(email):
    client = Groq(api_key=GROQ_API_KEY)
    prompt = f"""Classify this job email. Rules:
- Auto-replies confirming receipt = IRRELEVANT
- Only REJECTED if explicitly not moving forward
- Only MOVING_FORWARD if explicitly inviting next steps

{EXAMPLES}

From: {email['sender']}
Subject: {email['subject']}
Body: {email['body']}

Reply: CATEGORY | COMPANY | summary
Categories: OFFER, MOVING_FORWARD, REJECTED, IRRELEVANT"""
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80,
    )
    return r.choices[0].message.content.strip()

def send_telegram(token, chat_id, label, company, summary):
    try:
        msg = f"JOB ALERT\n{label}\n\nCompany: {company}\nSummary: {summary}"
        requests.get(
            f"https://api.telegram.org/bot{token}/sendMessage",
            params={"chat_id": chat_id, "text": msg},
            timeout=5,
        )
    except Exception as e:
        print(f"Telegram error: {e}")

def agent_loop(email, creds_data, tg_token, chat_id):
    seen = set()
    lmap = {"OFFER": "OFFER RECEIVED", "MOVING_FORWARD": "MOVING FORWARD", "REJECTED": "REJECTED"}
    print(f"[agent] started for {email}")
    while active_agents.get(email, {}).get("running"):
        try:
            svc = get_gmail_service(creds_data)
            for em in get_unread_emails(svc):
                if em["id"] in seen:
                    continue
                result = classify_email(em)
                parts = result.split("|")
                if len(parts) >= 3:
                    cat = parts[0].strip().upper()
                    co  = parts[1].strip()
                    sm  = parts[2].strip()
                    if cat in lmap:
                        send_telegram(tg_token, chat_id, lmap[cat], co, sm)
                        print(f"[agent] alert: {cat} | {co}")
                seen.add(em["id"])
                time.sleep(2)
        except Exception as e:
            print(f"[agent] error: {e}")
        time.sleep(300)
    print(f"[agent] stopped for {email}")

# ── routes ──────────────────────────────────────────────

@app.route("/")
def index():
    user = session.get("email")
    running = bool(active_agents.get(user, {}).get("running"))
    return render_template("index.html", user=user, running=running)

@app.route("/login")
def login():
    flow = make_flow()
    flow.code_verifier = ""
    auth_url, state = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )
    session["state"] = state
    return redirect(auth_url)

@app.route("/callback")
def callback():
    try:
        state = session["state"]
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            CLIENT_CONFIG, scopes=SCOPES, state=state, redirect_uri=REDIRECT_URI
        )
        # Use the authorization code directly
        code = request.args.get("code")
        flow.code_verifier = ""
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Get user email from token info
        req = google.auth.transport.requests.Request()
        id_info = google.oauth2.id_token.verify_oauth2_token(
            creds.id_token, req, CLIENT_ID,
            clock_skew_in_seconds=10
        )
        email = id_info["email"]

        session["email"] = email
        session["creds"] = {"token": creds.token, "refresh_token": creds.refresh_token}
        return redirect(url_for("setup"))
    except Exception as e:
        print(f"Callback error: {e}")
        return f"<h2>Auth error: {e}</h2><a href='/'>Try again</a>"

@app.route("/setup", methods=["GET", "POST"])
def setup():
    if "email" not in session:
        return redirect(url_for("index"))
    if request.method == "POST":
        tg_token = request.form["telegram_token"].strip()
        chat_id  = request.form["chat_id"].strip()
        email    = session["email"]
        creds    = session["creds"]
        if email in active_agents:
            active_agents[email]["running"] = False
            time.sleep(0.5)
        active_agents[email] = {"running": True}
        t = threading.Thread(
            target=agent_loop,
            args=(email, creds, tg_token, chat_id),
            daemon=True,
        )
        t.start()
        return redirect(url_for("dashboard"))
    return render_template("setup.html", user=session["email"])

@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect(url_for("index"))
    email = session["email"]
    running = bool(active_agents.get(email, {}).get("running"))
    return render_template("dashboard.html", user=email, running=running)

@app.route("/stop")
def stop():
    email = session.get("email")
    if email in active_agents:
        active_agents[email]["running"] = False
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    email = session.get("email")
    if email in active_agents:
        active_agents[email]["running"] = False
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
