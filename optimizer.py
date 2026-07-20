import gurobipy as gp
from gurobipy import GRB

from network import Network


def solve_flux_control(network, line_switching: bool = True):
    """
    Solve the minimum-cost redispatch problem for the given network.

    Parameters
    ----------
    network : Network
        Populated Network instance.
    line_switching : bool, default True
        If True, lines can be switched off (binary variables).
        Set to False when solving fluxcontrol.eu levels — the game only accepts
        injection adjustments, not topology changes.
    """
    nodes       = network.nodes
    lines       = network.lines
    power0      = network.power0
    cost_up     = network.cost_up
    cost_down   = network.cost_down
    power_limit = network.power_limit

    F_max = max(power_limit.values())
    M = F_max * (len(nodes) - 1)

    m = gp.Model("flux_control")
    m.Params.OutputFlag = 1

    p_up   = m.addVars(nodes, lb=0, name="p_up")
    p_down = m.addVars(nodes, lb=0, name="p_down")
    theta  = m.addVars(nodes, lb=-GRB.INFINITY, name="theta")
    flow   = m.addVars(lines.keys(), lb=-GRB.INFINITY, name="flow")

    if line_switching:
        line_on = m.addVars(lines.keys(), vtype=GRB.BINARY, name="line_on")
    else:
        # All lines fixed on — pure LP, no topology changes
        line_on = {l: 1 for l in lines}

    m.setObjective(
        gp.quicksum(cost_up[i] * p_up[i] + cost_down[i] * p_down[i] for i in nodes),
        GRB.MINIMIZE,
    )

    for i in nodes:
        outgoing = gp.quicksum(flow[l] for l, (a, b) in lines.items() if a == i)
        incoming = gp.quicksum(flow[l] for l, (a, b) in lines.items() if b == i)
        m.addConstr(power0[i] + p_up[i] - p_down[i] == outgoing - incoming,
                    name=f"node_balance[{i}]")

    for l, (a, b) in lines.items():
        F = power_limit[l]
        if line_switching:
            lo = line_on[l]
            m.addConstr(flow[l] <=  F * lo,            name=f"flow_ub[{l}]")
            m.addConstr(flow[l] >= -F * lo,            name=f"flow_lb[{l}]")
            m.addConstr(flow[l] - (theta[a] - theta[b]) <=  M * (1 - lo), name=f"dc_ub[{l}]")
            m.addConstr(flow[l] - (theta[a] - theta[b]) >= -M * (1 - lo), name=f"dc_lb[{l}]")
        else:
            m.addConstr(flow[l] <=  F,                 name=f"flow_ub[{l}]")
            m.addConstr(flow[l] >= -F,                 name=f"flow_lb[{l}]")
            m.addConstr(flow[l] == theta[a] - theta[b], name=f"dc[{l}]")

    m.addConstr(theta[nodes[0]] == 0, name="reference_angle")

    # ── connectivity constraints (line_switching only) ────────────────────────
    # Auxiliary flow q_conn proves every node stays reachable from the root
    # through switched-on lines. Not physical power — purely a graph-connectivity
    # certificate. Each non-root node must absorb exactly 1 unit; the root injects K.
    if line_switching:
        root = nodes[0]
        K    = len(nodes) - 1

        q_conn = m.addVars(lines.keys(), lb=-GRB.INFINITY, name="q_conn")

        # q_conn is zero on switched-off lines
        for l, (a, b) in lines.items():
            m.addConstr(q_conn[l] <=  K * line_on[l], name=f"conn_ub[{l}]")
            m.addConstr(q_conn[l] >= -K * line_on[l], name=f"conn_lb[{l}]")

        # root injects K units into the connectivity flow
        out_root = gp.quicksum(q_conn[l] for l, (a, b) in lines.items() if a == root)
        in_root  = gp.quicksum(q_conn[l] for l, (a, b) in lines.items() if b == root)
        m.addConstr(out_root - in_root == K, name="conn_balance_root")

        # every other node absorbs exactly 1 unit
        for i in nodes:
            if i == root:
                continue
            out_i = gp.quicksum(q_conn[l] for l, (a, b) in lines.items() if a == i)
            in_i  = gp.quicksum(q_conn[l] for l, (a, b) in lines.items() if b == i)
            m.addConstr(out_i - in_i == -1, name=f"conn_balance[{i}]")

    m.optimize()

    if m.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Optimization ended with status {m.Status}")

    return {
        "objective": m.ObjVal,
        "p_up":    {i: p_up[i].X   for i in nodes},
        "p_down":  {i: p_down[i].X  for i in nodes},
        "power":   {i: power0[i] + p_up[i].X - p_down[i].X for i in nodes},
        "theta":   {i: theta[i].X   for i in nodes},
        "flow":    {l: flow[l].X    for l in lines},
        "line_on": {l: (round(line_on[l].X) if hasattr(line_on[l], "X") else line_on[l])
                    for l in lines},
        "q_conn":  {l: q_conn[l].X  for l in lines} if line_switching else None,
    }


if __name__ == "__main__":
    # ── small 4-node example ────────────────────────────────────────────────
    net = Network()
    n0 = net.add_node(power0=80,  cost_up=100, cost_down=5)
    n1 = net.add_node(power0=100, cost_up=20,  cost_down=50)
    n2 = net.add_node(power0=-20, cost_up=200, cost_down=100)
    n3 = net.add_node(power0=-20, cost_up=200, cost_down=100)
    net.add_line(n0, n1, power_limit=50, name="AB")
    net.add_line(n1, n3, power_limit=50, name="BD")
    net.add_line(n0, n2, power_limit=50, name="AC")
    net.add_line(n2, n3, power_limit=50, name="CD")

    solution = solve_flux_control(net)

    for key, value in solution.items():
        print(f"\n{key}")
        print(value)

    net.visualize_comparison(solution=solution, title="4-node network — optimal solution")

