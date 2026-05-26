with open('app.py', 'r') as f:
    content = f.read()

old = '''@app.route("/callback")
def callback():'''

new = '''@app.route("/callback")
def callback():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"'''

content = content.replace(old, new)

# Fix fetch_token to use code directly
content = content.replace(
    'flow.fetch_token(authorization_response=auth_resp)',
    'flow.fetch_token(code=request.args.get("code"))'
)

with open('app.py', 'w') as f:
    f.write(content)
print('Done!')
