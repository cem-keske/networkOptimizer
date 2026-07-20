"""
flux_importer.py
----------------
Converts fluxcontrol.eu game data into a Network instance ready for solve_flux_control().

Typical workflow
----------------
1. Open fluxcontrol.eu and load a level.
2. Click the bookmarklet (see BOOKMARKLET below, or run: python solve_level.py --bookmarklet).
   → The current level's network JSON is copied to your clipboard.
3. In Python / a notebook:

       from flux_importer import from_clipboard
       from optimizer import solve_flux_control

       net = from_clipboard()
       sol = solve_flux_control(net)
       net.visualize_comparison(sol, title="Level X")

Field mapping (game → Network)
-------------------------------
  nodes[id].injection      → power0
  nodes[id].cost_increase  → cost_up
  nodes[id].cost_decrease  → cost_down
  nodes[id].x / .y         → node_pos  (Three.js y-up, matches matplotlib directly)
  lines[id].limit          → power_limit
  lines[id].from_node /
           .to_node        → line endpoints  (node names "N{id}")
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Union

from network import Network


# ---------------------------------------------------------------------------
# Core converter
# ---------------------------------------------------------------------------

def from_dict(data: dict) -> Network:
    """Convert a parsed fluxcontrol.eu sessionStorage dict to a Network instance.

    Parameters
    ----------
    data : dict
        The parsed JSON object stored under the 'network' key in sessionStorage.
        Must contain 'nodes' and 'lines' sub-dicts.

    Returns
    -------
    Network
        Populated Network with power0, cost_up/down, power_limit, node_pos, and
        an extra attribute `initial_flows` (dict line_id -> float) for reference.
    """
    net = Network()

    nodes_raw = data["nodes"]
    lines_raw = data["lines"]

    # --- nodes ---------------------------------------------------------------
    for node_id, nd in nodes_raw.items():
        name = f"N{node_id}"
        net.add_node(
            power0    = nd["injection"],
            cost_up   = nd["cost_increase"],
            cost_down = nd["cost_decrease"],
            name      = name,
        )
        # Game stores positions in Three.js world coords (y-up convention),
        # which already matches matplotlib's y-up axis — no flip needed.
        net.node_pos[name] = (nd["x"], nd["y"])

    # --- lines ---------------------------------------------------------------
    for line_id, ln in lines_raw.items():
        from_name = f"N{ln['from_node']}"
        to_name   = f"N{ln['to_node']}"
        net.add_line(from_name, to_name, power_limit=ln["limit"], name=line_id)

    # Keep a copy of the pre-redispatch flows for diagnostics
    net.initial_flows = {lid: ln["flow"] for lid, ln in lines_raw.items()}

    return net


# ---------------------------------------------------------------------------
# Convenience loaders
# ---------------------------------------------------------------------------

def from_json_string(text: str) -> Network:
    """Parse a raw JSON string (the value of sessionStorage['network']) into a Network."""
    return from_dict(json.loads(text))


def from_clipboard() -> Network:
    """Read the network JSON from the system clipboard and return a Network.

    Works on Windows (powershell), macOS (pbpaste), and Linux (xclip/xsel).
    The clipboard content should be the raw JSON string copied by the bookmarklet.
    """
    text = _read_clipboard()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Clipboard does not contain valid JSON. "
            "Did you click the bookmarklet on the fluxcontrol.eu tab?"
        ) from exc
    return from_dict(data)


def from_file(path: str) -> Network:
    """Load a network JSON file (e.g. exported via the bookmarklet's save option)."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return from_dict(data)


# ---------------------------------------------------------------------------
# Internal clipboard helper
# ---------------------------------------------------------------------------

def _read_clipboard() -> str:
    """Return clipboard text, trying multiple platform methods."""
    # Windows
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, check=True,
            )
            return result.stdout.strip()
        except Exception:
            pass

    # macOS
    if sys.platform == "darwin":
        try:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
            return result.stdout
        except Exception:
            pass

    # Linux – xclip
    try:
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout
    except Exception:
        pass

    # Linux – xsel
    try:
        result = subprocess.run(
            ["xsel", "--clipboard", "--output"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout
    except Exception:
        pass

    # Last resort: tkinter
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
        return text
    except Exception:
        pass

    raise RuntimeError(
        "Could not read clipboard. Install pyperclip (pip install pyperclip) "
        "or xclip/xsel on Linux."
    )


# ---------------------------------------------------------------------------
# Bookmarklet
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Two bookmarklet variants
# ---------------------------------------------------------------------------

# BOOKMARKLET_DOWNLOAD  — triggers a browser "Save As" for network.json.
# Recommended: drag this to your bookmarks bar, click it on the game page,
# save the file somewhere, then run:  python solve_level.py path/to/network.json
BOOKMARKLET_DOWNLOAD = (
    "javascript:(function(){"
    "var raw=sessionStorage.getItem('network');"
    "if(!raw){alert('No network data — load a level first.');return;}"
    "var d=JSON.parse(raw);"
    "var fname='level'+(d.level||'X')+'.json';"
    "var a=document.createElement('a');"
    "a.href='data:application/json,'+encodeURIComponent(raw);"
    "a.download=fname;"
    "document.body.appendChild(a);"
    "a.click();"
    "document.body.removeChild(a);"
    "})();"
)

# BOOKMARKLET_COPY  — tries navigator.clipboard, then falls back to showing
# the JSON in a prompt box the user can Ctrl+A / Ctrl+C from.
# After copying, run:  python solve_level.py
BOOKMARKLET_COPY = (
    "javascript:(function(){"
    "var raw=sessionStorage.getItem('network');"
    "if(!raw){alert('No network data — load a level first.');return;}"
    "function fallback(){window.prompt('Copy this JSON, then run: python solve_level.py',raw);}"
    "if(navigator.clipboard&&navigator.clipboard.writeText){"
    "navigator.clipboard.writeText(raw).then("
    "function(){alert('Copied to clipboard!\\nRun: python solve_level.py');},"
    "fallback);"
    "}else{fallback();}"
    "})();"
)

# Default alias — download is the most reliable cross-platform option
BOOKMARKLET = BOOKMARKLET_DOWNLOAD
