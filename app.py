import asyncio
from collections import defaultdict
import json
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    make_response,
    jsonify,
)
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

app = Flask(__name__)

MCP_URL = "https://mcp.hackthebox.ai/v1/ctf/mcp/"


# Async MCP session helper
async def _mcp_call(token, tool, params=None):
    async with streamablehttp_client(
        MCP_URL, headers={"Authorization": f"Bearer {token}"}
    ) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            if tool == "list_tools":
                return await session.list_tools()

            result = await session.call_tool(tool, params)
            return json.loads(result.content[0].text)


# Synchronous wrapper for Flask
def mcp_call(token, tool, params=None):
    try:
        return asyncio.run(_mcp_call(token, tool, params or {}))
    except Exception as e:
        return {"error": "exception", "error_description": str(e)}


@app.route("/tools")
def list_tools():
    token = request.cookies.get("token")
    if not token:
        return redirect("/login")
    tools = mcp_call(token, "list_tools")
    if "error" in tools:
        return render_template("error.html", error=tools)
    tool_names = [tool.name for tool in tools.tools]
    return jsonify(tool_names)


@app.route("/")
def home():
    token = request.cookies.get("token")
    if not token:
        return redirect("/login")
    events = mcp_call(token, "list_ctf_events")
    print(json.dumps(events))
    if "error" in events:
        return render_template("error.html", error=events)
    return render_template("index.html", events=events)


@app.route("/login", methods=["GET"])
def home_login():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    token = request.form.get("token")
    if token:
        resp = make_response(redirect("/"))
        resp.set_cookie("token", token)
        return resp
    return redirect("/login")


@app.route("/join/<int:event_id>")
def join(event_id):
    token = request.cookies.get("token")
    teams = mcp_call(token, "retrieve_my_teams")
    join = mcp_call(
        token,
        "join_ctf_event",
        {
            "ctf_id": event_id,
            "team_id": teams[0].get("id"),
            "consent": True,
            "ctf_password": None,
        },
    )
    if "error" in join:
        return render_template("error.html", error=join)
    return redirect("/")


@app.route("/event/<int:event_id>")
def event(event_id):
    token = request.cookies.get("token")
    details = mcp_call(token, "retrieve_ctf", {"ctf_id": event_id})
    if "error" in details:
        return render_template("error.html", error=details)

    challenges = details.get("challenges", [])
    difficulty_order = ["sanity check", "very easy", "easy", "medium", "hard"]

    # Group challenges by category and difficulty
    categories = defaultdict(lambda: defaultdict(list))
    for c in challenges:
        categories[c["challenge_category_id"]][c["difficulty"]].append(c)

    # Convert to a dict of {category_id: {"name": category_name, "difficulties": {...}}}
    grouped = {
        cat_id: {
            "name": categorie_name(cat_id),
            "difficulties": {
                diff: categories[cat_id][diff]
                for diff in difficulty_order
                if categories[cat_id][diff]
            },
        }
        for cat_id in categories
    }

    return render_template(
        "event.html",
        event_name=details.get("name"),
        grouped=grouped,
        difficulty_order=difficulty_order,
        event_id=event_id,
    )


@app.route("/scoreboard/<int:event_id>")
def scoreboard(event_id):
    token = request.cookies.get("token")
    details = mcp_call(token, "retrieve_ctf_scores", {"ctf_id": event_id})
    if "error" in details:
        return render_template("error.html", error=details)
    return render_template("scoreboard.html", details=details)


@app.route("/challenge/<int:event_id>/<int:chal_id>")
def challenge(event_id, chal_id):
    token = request.cookies.get("token")
    details = mcp_call(token, "retrieve_ctf", {"ctf_id": event_id})
    if "error" in details:
        return render_template("error.html", error=details)
    download_link = mcp_call(token, "get_download_link", {"challenge_id": chal_id})
    challenge_data = {}
    for chall in details.get("challenges", []):
        if chall.get("id") == chal_id:
            challenge_data = chall
            break
    return render_template(
        "challenge.html",
        chal_id=chal_id,
        event_id=event_id,
        chal=challenge_data,
        download_link=download_link,
        categorie_name=categorie_name,
    )


@app.route("/start_container/<int:chal_id>")
def start_container(chal_id):
    token = request.cookies.get("token")
    result = mcp_call(token, "start_container", {"challenge_id": chal_id})
    return render_template("generic.html", result=result)


@app.route("/stop_container/<int:chal_id>")
def stop_container(chal_id):
    token = request.cookies.get("token")
    result = mcp_call(token, "stop_container", {"challenge_id": chal_id})
    return render_template("generic.html", result=result)


@app.route("/submit_flag/<int:chal_id>", methods=["POST"])
def submit_flag(chal_id):
    token = request.cookies.get("token")
    flag = request.form.get("flag")
    result = mcp_call(token, "submit_flag", {"challenge_id": chal_id, "flag": flag})
    return render_template("generic.html", result=result)


categories = {
    2: "Web",
    3: "Pwn",
    4: "Crypto",
    5: "Reverse",
    7: "Forensics",
    8: "Misc",
    11: "Coding",
    14: "Blockchain",
    15: "Hardware",
    16: "Warmup",
    21: "ICS",
}


def categorie_name(categorie_id):
    if categorie_id in categories:
        return categories[categorie_id]
    return categorie_id


if __name__ == "__main__":
    app.run(debug=True)
