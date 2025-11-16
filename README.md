# Web interface for HTB CTF (MCP only)

## Requirements

* Flask
* MCP Python client

### Install dependencies

```bash
pip install Flask mcp[cli]
```

---

## Usage

1. Clone the repository:

```bash
git clone https://github.com/nicolas-duhamel/htb-mcp-interface.git
cd htb-mcp-interface
```

2. Run the Flask app:

```bash
python app.py
```

3. Open your browser and go to:

```
http://127.0.0.1:5000/login
```

4. Enter your MCP token on the login page.

5. Browse CTF events, join, view challenges, spawn Docker environments, submit flags, and check the scoreboard.

---

