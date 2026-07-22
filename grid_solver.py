#!/usr/bin/env python3
"""
grid_solver.py
--------------
One-shot FluxControl level solver.

Usage
-----
  # Normal use: click bookmarklet on the game page, then:
  python grid_solver.py

  # Load from a saved JSON file instead of clipboard:
  python grid_solver.py path/to/level.json

  # Disable line switching (LP instead of MILP):
  python grid_solver.py --no-switching

  # Print the bookmarklet URLs (drag to your bookmarks bar):
  python grid_solver.py --bookmarklet
"""

import sys

from flux_importer import BOOKMARKLET, from_clipboard, from_file
from optimizer import solve_flux_control


# ---------------------------------------------------------------------------
# Pretty printer
# ---------------------------------------------------------------------------

def print_solution(solution: dict, network) -> None:
    sep = "=" * 54

    print(f"\n{sep}")
    print(f"  Optimal redispatch   (total cost = {solution['objective']:.2f} EUR)")
    print(sep)

    print("\nNode adjustments:")
    any_action = False
    for node in network.nodes:
        up   = abs(solution["p_up"][node])
        down = abs(solution["p_down"][node])
        p0   = network.power0[node]
        pf   = solution["power"][node]
        if up > 1e-3:
            cost = network.cost_up[node] * up
            print(f"  {node}  UP  +{up:.2f} MW   {p0:+.1f} -> {pf:+.1f} MW   cost {cost:.2f} EUR")
            any_action = True
        elif down > 1e-3:
            cost = network.cost_down[node] * down
            print(f"  {node}  DN  -{down:.2f} MW   {p0:+.1f} -> {pf:+.1f} MW   cost {cost:.2f} EUR")
            any_action = True
        else:
            print(f"  {node}  -- no change   ({p0:+.1f} MW)")
    if not any_action:
        print("  (no redispatch needed -- network already feasible)")

    print("\nLine flows after redispatch:")
    for line, flow in solution["flow"].items():
        limit  = network.power_limit[line]
        pct    = 100 * abs(flow) / limit
        init   = getattr(network, "initial_flows", {}).get(line)
        init_s = f"  (was {init:+.2f} MW)" if init is not None else ""
        if abs(flow) > limit + 1e-3:
            flag = "[OVERLOADED]"
        elif pct > 90:
            flag = "[near-limit]"
        else:
            flag = "[ok]"
        on = solution["line_on"].get(line, 1)
        on_s = "" if on else "  [SWITCHED OFF]"
        print(f"  {line:8s}  {flow:+7.2f} MW  ({pct:5.1f}% of {limit} MW)  {flag}{on_s}{init_s}")

    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = sys.argv[1:]

    # -- print bookmarklets --------------------------------------------------
    if "--bookmarklet" in args:
        from flux_importer import BOOKMARKLET_DOWNLOAD, BOOKMARKLET_COPY
        print("\n--- DOWNLOAD bookmarklet (recommended) ---")
        print("Drag this URL to your bookmarks bar.")
        print("Clicking it saves a level<N>.json file -- then run:")
        print("  python grid_solver.py level<N>.json\n")
        print(BOOKMARKLET_DOWNLOAD)
        print("\n--- COPY bookmarklet (clipboard fallback) ---")
        print("Clicking it copies the JSON; then run:  python grid_solver.py\n")
        print(BOOKMARKLET_COPY)
        sys.exit(0)

    # -- load network --------------------------------------------------------
    file_args = [a for a in args if not a.startswith("--")]
    if file_args:
        path = file_args[0]
        print(f"Loading network from file: {path}")
        net = from_file(path)
    else:
        print("Reading network JSON from clipboard...")
        net = from_clipboard()

    print(f"Loaded: {net}")
    print(f"  Nodes : {net.nodes}")
    print(f"  Lines : {list(net.lines.keys())}")
    if hasattr(net, "initial_flows"):
        print("  Initial flows:")
        for lid, f in net.initial_flows.items():
            lim = net.power_limit[lid]
            pct = 100 * abs(f) / lim
            flag = " [OVERLOADED]" if abs(f) > lim + 1e-3 else (" [near-limit]" if pct > 90 else "")
            print(f"    {lid:8s}  {f:+.2f} MW  ({pct:.1f}%){flag}")

    # -- solve ---------------------------------------------------------------
    switching = "--no-switching" not in args
    if switching:
        print("Line switching enabled (MILP).")
    else:
        print("Line switching disabled (LP).")
    solution = solve_flux_control(net, line_switching=switching)
    print_solution(solution, net)

    # -- visualise -----------------------------------------------------------
    net.visualize_comparison(solution, title="FluxControl -- optimal redispatch")
