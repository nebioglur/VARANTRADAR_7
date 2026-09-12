import os

with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'def index():'
idx = text.find(target)
if idx != -1:
    # Need to find the route decorator above it
    target_route = '@app.route("/")'
    route_idx = text.rfind(target_route, 0, idx)
    
    insert = """
@app.route("/v8")
@login_required
def v8_dashboard():
    response = make_response(send_from_directory("ui", "v8_dashboard.html"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response
"""
    if 'def v8_dashboard():' not in text:
        text = text[:route_idx] + insert + "\n" + text[route_idx:]
        with open('server.py', 'w', encoding='utf-8') as f:
            f.write(text)
        print('V8 UI route added.')
    else:
        print('Already exists')
else:
    print('Target not found')
