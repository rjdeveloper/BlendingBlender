# Setup Instructions for Blender MCP Agent

### 1. Download & Install Blender
-   Download Blender (v3.0 or newer) from the official site: [blender.org/download](https://www.blender.org/download/)
-   Install it on your system.

### 2. Install Blender Add-on
-   Download `addon.py` from [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp/blob/main/addon.py).
-   In Blender: `Edit > Preferences > Add-ons > Install...` and select `addon.py`.
-   Enable "Interface: Blender MCP".
-   In the Blender Sidebar (N), go to "BlenderMCP" and click **Connect to Claude** (this starts the socket server).

### 3. Install UV (Environment Manager)
If you don't have `uv` installed yet:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 4. Initialize UV Environment
In the project directory (`c:\blundai`), run:
```bash
uv sync
```

### 5. Run the Project
You must run both the backend and frontend within the `uv` environment:

**Start Backend (FastAPI):**
```bash
uv run python backend.py
```

**Start Frontend (Streamlit):**
```bash
uv run streamlit run frontend.py
```

### Note on DWG Export
Blender does not export `.dwg` natively. The agent is instructed to:
1.  Create the design in Blender.
2.  Export to `.dxf` (AutoCAD compatible) or `.stl`.
3.  Advise on using external converters for `.dwg` if needed.
4.  If you have a specific Blender add-on for DWG export, the agent can use `execute_blender_code` to trigger it.
