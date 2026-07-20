import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx


class Network:
    """Simple network helper to manage nodes and lines.

    Features:
    - add_node(power0, cost_up, cost_down, name=None): add a node with initial power and redispatch costs
    - add_line(a, b, power_limit, name=None): add an (undirected) line between existing nodes
      with a MW capacity limit, auto-naming if name is None
    - adjacency_matrix(): returns an NxN list-of-lists (0/1) showing connections
    - visualize_comparison(solution, title): before/after subplot

    The class keeps insertion order for nodes and assigns indices 0..N-1.
    Lines are stored in a dict {line_name: (a, b)} using the node names.
    Up/down costs and initial power are stored per node in cost_up, cost_down, and power0 dicts.
    Line capacities are stored in power_limit {line_name: max_flow_MW}.
    """

    def __init__(self):
        self.nodes = []
        self.node_idx = {}     # name -> index
        self.lines = {}        # name -> (a, b)
        self.cost_up = {}      # name -> cost_per_MW_up
        self.cost_down = {}    # name -> cost_per_MW_down
        self.power0 = {}       # name -> initial power injection [MW]
        self.power_limit = {}  # line_name -> max flow [MW]
        self.node_pos = {}     # name -> (x, y) in plot coords (optional; set by importers)
        self._line_counter = 0

    def add_node(self, power0, cost_up, cost_down, name=None):
        """Add a node with its initial power injection and redispatch costs.
        Auto-names 'N{index}' when name is None.
        Returns the name; silently returns existing name if already present."""
        if name is None:
            name = f"N{len(self.nodes)}"
        if name in self.node_idx:
            return name
        self.node_idx[name] = len(self.nodes)
        self.nodes.append(name)
        self.power0[name] = power0
        self.cost_up[name] = cost_up
        self.cost_down[name] = cost_down
        return name

    def add_line(self, a, b, power_limit, name=None):
        """Add an undirected line between existing nodes a and b with a MW capacity limit.
        Auto-names 'L{counter}' when name is None. Returns the line name."""
        if a not in self.node_idx:
            raise KeyError(f"Node '{a}' does not exist")
        if b not in self.node_idx:
            raise KeyError(f"Node '{b}' does not exist")
        if name is None:
            name = f"L{self._line_counter}"
            self._line_counter += 1
            while name in self.lines:
                name = f"L{self._line_counter}"
                self._line_counter += 1
        self.lines[name] = (a, b)
        self.power_limit[name] = power_limit
        return name

    def adjacency_matrix(self):
        """Return NxN adjacency matrix as a list-of-lists (0/1 integers)."""
        n = len(self.nodes)
        mat = [[0] * n for _ in range(n)]
        for a, b in self.lines.values():
            i, j = self.node_idx[a], self.node_idx[b]
            mat[i][j] = mat[j][i] = 1
        return mat

    # ── internal helpers ──────────────────────────────────────────────────────

    def _build_graph(self):
        G = nx.Graph()
        G.add_nodes_from(self.nodes)
        for lname, (a, b) in self.lines.items():
            G.add_edge(a, b, key=lname)
        return G

    @staticmethod
    def _node_color(value, max_abs):
        t = value / max_abs if max_abs else 0
        t = max(-1.0, min(1.0, t))
        if t >= 0:
            return mcolors.to_hex((1.0, 1.0 - t, 1.0 - t))  # white → red
        else:
            return mcolors.to_hex((1.0 + t, 1.0 + t, 1.0))  # white → blue

    # ── drawing helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _edge_line_map(lines):
        """Build both-direction (a,b) / (b,a) → line_name lookup."""
        m = {}
        for l, (a, b) in lines.items():
            m[(a, b)] = l
            m[(b, a)] = l
        return m

    def _draw_edges(self, ax, G, pos, edge_line, flows, line_on=None):
        """Draw edges coloured by flow loading. Returns edge_labels dict."""
        edge_colors, edge_widths, edge_styles = [], [], []
        edge_labels = {}

        for a, b in G.edges():
            l = edge_line.get((a, b)) or edge_line.get((b, a))
            lim  = self.power_limit.get(l, 1)
            f    = flows.get(l)
            on   = (line_on.get(l, 1) if line_on else 1)

            if on == 0:
                edge_colors.append("#bbbbbb")
                edge_widths.append(1.0)
                edge_styles.append("dashed")
                edge_labels[(a, b)] = "OFF"
                continue

            edge_styles.append("solid")
            if f is not None:
                pct = 100 * abs(f) / lim
                if pct > 100:
                    edge_colors.append("#cc2200")
                    edge_widths.append(3.5)
                    flag = "(!)"
                elif pct > 90:
                    edge_colors.append("#e07b39")
                    edge_widths.append(2.5)
                    flag = "(~)"
                else:
                    edge_colors.append("#444444")
                    edge_widths.append(1.8)
                    flag = ""
                edge_labels[(a, b)] = f"{f:+.1f}  {pct:.0f}%{flag}"
            else:
                edge_colors.append("#444444")
                edge_widths.append(1.8)
                edge_labels[(a, b)] = f"lim {lim}"

        # split solid / dashed for draw call
        solid  = [(a, b) for (a, b), s in zip(G.edges(), edge_styles) if s == "solid"]
        dashed = [(a, b) for (a, b), s in zip(G.edges(), edge_styles) if s == "dashed"]
        s_col  = [c for c, s in zip(edge_colors, edge_styles) if s == "solid"]
        s_wid  = [w for w, s in zip(edge_widths, edge_styles) if s == "solid"]

        if solid:
            nx.draw_networkx_edges(G, pos, edgelist=solid,  width=s_wid,
                                   edge_color=s_col, ax=ax)
        if dashed:
            nx.draw_networkx_edges(G, pos, edgelist=dashed, width=1.0,
                                   edge_color="#bbbbbb", style="dashed", ax=ax)

        lbbox = dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels,
                                     font_size=7, font_color="#222222",
                                     bbox=lbbox, ax=ax)
        return edge_labels

    def _draw_nodes(self, ax, G, pos, values, sublabels=None, node_size=1100):
        """Draw nodes with injection values inside and optional sub-labels above."""
        max_abs = max((abs(v) for v in values.values()), default=1) or 1
        colors  = [self._node_color(values[n], max_abs) for n in self.nodes]

        nx.draw_networkx_nodes(G, pos, node_color=colors,
                               node_size=node_size, linewidths=1.2,
                               edgecolors="#555555", ax=ax)

        # injection value inside node
        nx.draw_networkx_labels(G, pos,
                                labels={n: f"{values[n]:+g}" for n in self.nodes},
                                font_size=8, font_weight="bold", ax=ax)

        # node name above node
        offset = 0.07
        pos_above = {n: (xy[0], xy[1] + offset) for n, xy in pos.items()}
        nx.draw_networkx_labels(G, pos_above,
                                labels={n: n for n in self.nodes},
                                font_size=7, font_color="#666666", ax=ax)

        # optional sub-label below node (e.g. delta or cost)
        if sublabels:
            pos_below = {n: (xy[0], xy[1] - offset) for n, xy in pos.items()}
            nx.draw_networkx_labels(G, pos_below,
                                    labels={n: sublabels[n] for n in self.nodes
                                            if sublabels.get(n)},
                                    font_size=7, font_color="#cc3300", ax=ax)

    def _cost_table(self, ax):
        """Add a small cost legend in the bottom-left corner."""
        lines = ["Node  +c   -c"]
        for n in self.nodes:
            lines.append(f"{n:<5}  {self.cost_up[n]:>4}  {self.cost_down[n]:>4}")
        txt = "\n".join(lines)
        ax.text(0.01, 0.01, txt, transform=ax.transAxes,
                fontsize=7, fontfamily="monospace", va="bottom",
                bbox=dict(boxstyle="round,pad=0.4", fc="#f5f5f5",
                          ec="#cccccc", alpha=0.9))

    def _draw_before(self, ax, G, pos):
        """Left panel: initial state — power0, initial flows, costs table."""
        initial_flows = getattr(self, "initial_flows", {})
        edge_line     = self._edge_line_map(self.lines)

        self._draw_nodes(ax, G, pos, self.power0)
        self._draw_edges(ax, G, pos, edge_line, initial_flows)
        self._cost_table(ax)

        # legend patches
        patches = [
            mpatches.Patch(color="#cc2200", label="Overloaded (>100%)"),
            mpatches.Patch(color="#e07b39", label="Near limit (>90%)"),
            mpatches.Patch(color="#444444", label="OK"),
        ]
        ax.legend(handles=patches, loc="upper right", fontsize=7, framealpha=0.85)

        n_over = sum(1 for l, f in initial_flows.items()
                     if abs(f) > self.power_limit.get(l, float("inf")) + 1e-3)
        title = "Before  (MW inside nodes)"
        if n_over:
            title += f"  — {n_over} overloaded"
        ax.set_title(title, fontsize=11)
        ax.axis("off")

    def _draw_after(self, ax, G, pos, solution):
        """Right panel: optimised state — final power, flows, deltas."""
        power   = solution["power"]
        p_up    = solution["p_up"]
        p_down  = solution["p_down"]
        flow    = solution["flow"]
        line_on = solution["line_on"]

        edge_line = self._edge_line_map(self.lines)
        # line_on keyed by line name
        lo_by_name = {l: line_on.get(l, 1) for l in self.lines}

        # delta sub-labels (only for changed nodes)
        deltas = {}
        for n in self.nodes:
            if p_up[n] > 1e-4:
                deltas[n] = f"+{p_up[n]:.1f} MW"
            elif p_down[n] > 1e-4:
                deltas[n] = f"-{p_down[n]:.1f} MW"
            else:
                deltas[n] = ""

        self._draw_nodes(ax, G, pos, power, sublabels=deltas)
        self._draw_edges(ax, G, pos, edge_line, flow, line_on=lo_by_name)

        # legend
        patches = [
            mpatches.Patch(color="#cc2200", label="Overloaded (>100%)"),
            mpatches.Patch(color="#e07b39", label="Near limit (>90%)"),
            mpatches.Patch(color="#444444", label="OK"),
            mpatches.Patch(color="#bbbbbb", label="Switched off"),
        ]
        ax.legend(handles=patches, loc="upper right", fontsize=7, framealpha=0.85)

        n_switched = sum(1 for v in lo_by_name.values() if v == 0)
        title = f"After  (obj = {solution['objective']:.2f} EUR)"
        if n_switched:
            title += f"  — {n_switched} line(s) off"
        ax.set_title(title, fontsize=11)
        ax.axis("off")

    # ── public API ────────────────────────────────────────────────────────────

    def visualize_comparison(self, solution, title=None, figsize=None):
        """Draw before/after subplots for a solve_flux_control solution."""
        G = self._build_graph()

        # layout
        if self.node_pos:
            xs = [v[0] for v in self.node_pos.values()]
            ys = [v[1] for v in self.node_pos.values()]
            x0, x1 = min(xs), max(xs)
            y0, y1 = min(ys), max(ys)
            xr = (x1 - x0) or 1
            yr = (y1 - y0) or 1
            pos = {n: ((self.node_pos[n][0] - x0) / xr,
                       (self.node_pos[n][1] - y0) / yr)
                   for n in self.nodes if n in self.node_pos}
            missing = [n for n in self.nodes if n not in pos]
            if missing:
                pos.update(nx.spring_layout(G, seed=42, pos=pos,
                                            fixed=[n for n in self.nodes if n in pos]))
        else:
            pos = nx.spring_layout(G, seed=42)

        # auto-scale figure: more nodes/lines = more space needed
        n = len(self.nodes)
        if figsize is None:
            w = max(16, 3 * n)
            h = max(6,  2 * n - 2)
            figsize = (w, h)

        fig, (ax_before, ax_after) = plt.subplots(1, 2, figsize=figsize)

        # give labels room at the edges
        margin = 0.22
        for ax in (ax_before, ax_after):
            ax.set_xlim(-margin, 1 + margin)
            ax.set_ylim(-margin, 1 + margin)

        self._draw_before(ax_before, G, pos)
        self._draw_after(ax_after,  G, pos, solution)

        if title:
            fig.suptitle(title, fontsize=13, fontweight="bold")
        plt.tight_layout()
        plt.show()

    def __repr__(self):
        return f"Network(nodes={len(self.nodes)}, lines={len(self.lines)})"
