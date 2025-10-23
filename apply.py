# Student Name: Martin Tran
# Titan Email: 23martintran@csu.fullerton.edu=
# Project: CPSC 335 – Interactive Campus Navigation System
# Date: 2025-10-14

"""
Interactive Campus Navigation System (single-file)
Features:
- Create nodes (buildings) by name and place them with mouse clicks.
- Connect nodes with edges: distance, time, accessibility.
- Randomize weights (distance/time).
- Toggle edge closures (blocked/open).
- Accessibility-only mode to ignore non-accessible edges.
- BFS (fewest hops) and DFS (any path) with traversal order and path display.
- Visualization on Tkinter canvas with color codes:
    Green  -> Current BFS/DFS path (final)
    Red    -> Closed/blocked path
    Orange -> Non-accessible path
    Black  -> Open regular path
- Robust error handling for duplicate names, invalid selections, no path found, etc.
- Single file: apply.py
"""

import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
import random
from collections import deque

NODE_RADIUS = 18
EDGE_LINE_WIDTH = 3

# Color codes mapping
COLOR_REGULAR = "black"
COLOR_CLOSED = "red"
COLOR_NONACCESS = "orange"
COLOR_PATH = "green"
COLOR_VISITED = "blue"

class Node:
    def __init__(self, name, x, y, canvas_id=None, text_id=None):
        self.name = name
        self.x = x
        self.y = y
        self.canvas_id = canvas_id
        self.text_id = text_id

class Edge:
    def __init__(self, a_name, b_name, distance=1, time=1, accessible=True, closed=False, line_id=None, label_id=None):
        # undirected edge stored once with endpoints by name
        self.a = a_name
        self.b = b_name
        self.distance = distance
        self.time = time
        self.accessible = accessible
        self.closed = closed
        self.line_id = line_id
        self.label_id = label_id

    def other(self, name):
        return self.b if name == self.a else self.a

class Graph:
    def __init__(self):
        self.nodes = {}   # name -> Node
        self.edges = {}   # frozenset({a,b}) -> Edge

    def add_node(self, name, x, y):
        if name in self.nodes:
            raise ValueError(f"Duplicate node name '{name}'")
        self.nodes[name] = Node(name, x, y)

    def remove_node(self, name):
        if name not in self.nodes:
            return
        # remove edges incident
        to_remove = [k for k in self.edges if name in k]
        for k in to_remove:
            del self.edges[k]
        del self.nodes[name]

    def connect(self, a, b, distance=1, time=1, accessible=True):
        if a not in self.nodes or b not in self.nodes:
            raise ValueError("Both nodes must exist")
        k = frozenset({a, b})
        if a == b:
            raise ValueError("Cannot connect node to itself")
        if k in self.edges:
            raise ValueError("Edge already exists")
        self.edges[k] = Edge(a, b, distance, time, accessible)

    def disconnect(self, a, b):
        k = frozenset({a, b})
        if k in self.edges:
            del self.edges[k]

    def neighbors(self, name, accessible_only=False, allow_closed=False):
        res = []
        for k, e in self.edges.items():
            if name in k:
                if e.closed and not allow_closed:
                    continue
                if accessible_only and not e.accessible:
                    continue
                res.append(e.other(name))
        return res

    def get_edge(self, a, b):
        return self.edges.get(frozenset({a, b}))

    def randomize_weights(self, min_val=1, max_val=100):
        for e in self.edges.values():
            e.distance = random.randint(min_val, max_val)
            e.time = random.randint(min_val, max_val)

class App:
    def __init__(self, root):
        self.root = root
        root.title("Interactive Campus Navigation System — CPSC 335")
        self.graph = Graph()
        self.selected_node = None
        self.connect_mode = False
        self.connect_first = None
        self.edge_selection_mode = False
        self.selected_edge = None
        self.animation_speed = 200  # milliseconds between steps

        # Top frame for controls
        control_frame = ttk.Frame(root)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=6, pady=6)

        # Left controls
        leftframe = ttk.Frame(control_frame)
        leftframe.pack(side=tk.LEFT, anchor=tk.N)

        ttk.Label(leftframe, text="Node / Edge Tools").pack(anchor=tk.W)
        self.mode_label = ttk.Label(leftframe, text="Click canvas to add node", foreground="gray")
        self.mode_label.pack(anchor=tk.W, pady=(0,6))

        btn_row = ttk.Frame(leftframe)
        btn_row.pack(anchor=tk.W, pady=2)
        ttk.Button(btn_row, text="Toggle Connect Mode", command=self.toggle_connect_mode).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Toggle Edge Select", command=self.toggle_edge_selection_mode).pack(side=tk.LEFT, padx=(6,0))

        ttk.Button(leftframe, text="Randomize All Weights", command=self.on_randomize).pack(anchor=tk.W, pady=6)

        # BFS/DFS selection
        algo_frame = ttk.Frame(control_frame)
        algo_frame.pack(side=tk.LEFT, padx=12)
        ttk.Label(algo_frame, text="Search").pack(anchor=tk.W)
        self.start_var = tk.StringVar()
        self.goal_var = tk.StringVar()
        ttk.Entry(algo_frame, textvariable=self.start_var, width=10).pack(anchor=tk.W, pady=2)
        ttk.Entry(algo_frame, textvariable=self.goal_var, width=10).pack(anchor=tk.W, pady=2)
        ttk.Button(algo_frame, text="Run BFS", command=lambda: self.run_search("BFS")).pack(anchor=tk.W, pady=2)
        ttk.Button(algo_frame, text="Run DFS", command=lambda: self.run_search("DFS")).pack(anchor=tk.W, pady=2)

        # Right controls
        rightframe = ttk.Frame(control_frame)
        rightframe.pack(side=tk.RIGHT, anchor=tk.N)
        self.accessible_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(rightframe, text="Accessible Only", variable=self.accessible_only).pack(anchor=tk.E)
        ttk.Label(rightframe, text="Edge Info / Toggle").pack(anchor=tk.E, pady=(6,0))

        # Edge info panel
        edgepanel = ttk.Frame(rightframe, borderwidth=1, relief=tk.SUNKEN, padding=6)
        edgepanel.pack(anchor=tk.E, pady=4)
        ttk.Label(edgepanel, text="Selected Edge:").pack(anchor=tk.W)
        self.edge_label = ttk.Label(edgepanel, text="None")
        self.edge_label.pack(anchor=tk.W, pady=(0,4))
        ttk.Button(edgepanel, text="Toggle Closed/Open", command=self.toggle_selected_edge_closed).pack(fill=tk.X)
        ttk.Button(edgepanel, text="Toggle Accessible/Non", command=self.toggle_selected_edge_accessible).pack(fill=tk.X, pady=4)

        # Canvas area
        self.canvas = tk.Canvas(root, bg="white", width=900, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)

        # Bottom info area
        bottom = ttk.Frame(root)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        self.info_label = ttk.Label(bottom, text="Welcome! Left-click canvas to create a node.")
        self.info_label.pack(side=tk.LEFT, padx=6, pady=4)

        # Make a small legend
        legend = ttk.Frame(bottom)
        legend.pack(side=tk.RIGHT, padx=6)
        self._make_legend(legend)

        # For animation state
        self._anim_after_id = None

    def _make_legend(self, parent):
        ttk.Label(parent, text="Legend:").pack(side=tk.LEFT)
        canvas = tk.Canvas(parent, width=220, height=28, bg=parent.cget("background"), highlightthickness=0)
        canvas.pack(side=tk.LEFT)
        x = 5
        def box(color, label):
            nonlocal x
            canvas.create_rectangle(x,4,x+12,16, fill=color, outline="black")
            canvas.create_text(x+20,10, anchor=tk.W, text=label, font=("TkDefaultFont", 8))
            x += 80
        box(COLOR_PATH, "Final Path")
        box(COLOR_CLOSED, "Closed")
        box(COLOR_NONACCESS, "Non-access")
        box(COLOR_REGULAR, "Open")

    def toggle_connect_mode(self):
        self.connect_mode = not self.connect_mode
        self.connect_first = None
        if self.connect_mode:
            self.mode_label.config(text="Connect mode: select two nodes", foreground="brown")
        else:
            self.mode_label.config(text="Click canvas to add node", foreground="gray")
        self.info_label.config(text=f"Connect Mode {'ON' if self.connect_mode else 'OFF'}")

    def toggle_edge_selection_mode(self):
        self.edge_selection_mode = not self.edge_selection_mode
        if self.edge_selection_mode:
            self.mode_label.config(text="Edge select mode: right-click edge to select", foreground="purple")
        else:
            self.mode_label.config(text="Click canvas to add node", foreground="gray")
        self.info_label.config(text=f"Edge Selection Mode {'ON' if self.edge_selection_mode else 'OFF'}")

    def on_canvas_click(self, event):
        x, y = event.x, event.y
        # If in connect mode, try selecting a node if clicked on node; else add new node
        clicked = self._node_at_point(x, y)
        if self.connect_mode:
            if not clicked:
                self.info_label.config(text="Connect mode: click on existing nodes to connect.")
                return
            if self.connect_first is None:
                self.connect_first = clicked
                self.info_label.config(text=f"Selected first node: {clicked}")
            else:
                # second node selected -> ask for edge details and create
                a, b = self.connect_first, clicked
                if a == b:
                    messagebox.showerror("Invalid", "Cannot connect a node to itself.")
                    self.connect_first = None
                    return
                try:
                    self._ask_and_connect(a, b)
                except Exception as e:
                    messagebox.showerror("Error", str(e))
                self.connect_first = None
                self._redraw_all()
            return

        # Otherwise, add node
        name = simpledialog.askstring("Node name", "Enter building name (unique):", parent=self.root)
        if not name:
            return
        name = name.strip()
        if name == "":
            messagebox.showerror("Invalid name", "Node name cannot be empty.")
            return
        if name in self.graph.nodes:
            messagebox.showerror("Duplicate", f"A node named '{name}' already exists.")
            return
        self.graph.add_node(name, x, y)
        self._draw_node(self.graph.nodes[name])
        self.info_label.config(text=f"Added node '{name}' at ({x},{y})")

    def on_canvas_right_click(self, event):
        # Right-click could be used to select an edge (or toggle closure)
        x, y = event.x, event.y
        if self.edge_selection_mode:
            # find nearest edge within threshold
            found = self._edge_at_point(x, y)
            if not found:
                self.info_label.config(text="No edge near clicked point.")
                self.selected_edge = None
                self.edge_label.config(text="None")
                return
            a,b,e = found
            self.selected_edge = (a,b)
            self.edge_label.config(text=f"{a} ↔ {b} | dist={e.distance} time={e.time} acc={'Y' if e.accessible else 'N'} closed={'Y' if e.closed else 'N'}")
            self.info_label.config(text=f"Selected edge {a} ↔ {b}")
            return
        # Default right-click toggles closure if on an edge, else ignore
        found = self._edge_at_point(x, y)
        if found:
            a,b,e = found
            e.closed = not e.closed
            self.info_label.config(text=f"Toggled edge {a} ↔ {b} to {'CLOSED' if e.closed else 'OPEN'}")
            self._redraw_all()

    def _ask_and_connect(self, a, b):
        # Popup to gather distance/time/accessibility
        dlg = EdgeDialog(self.root, a, b)
        self.root.wait_window(dlg.top)
        if dlg.result is None:
            # cancelled
            return
        distance, time_v, accessible = dlg.result
        try:
            self.graph.connect(a, b, distance=distance, time=time_v, accessible=accessible)
        except ValueError as e:
            messagebox.showerror("Edge error", str(e))

    def _draw_node(self, node: Node):
        x, y = node.x, node.y
        cid = self.canvas.create_oval(x - NODE_RADIUS, y - NODE_RADIUS, x + NODE_RADIUS, y + NODE_RADIUS, fill="white", outline="black", width=2)
        tid = self.canvas.create_text(x, y, text=node.name, font=("TkDefaultFont", 9))
        node.canvas_id = cid
        node.text_id = tid

    def _redraw_all(self):
        # clear canvas and redraw nodes and edges and labels
        self.canvas.delete("all")
        # draw edges first
        for k, e in self.graph.edges.items():
            a, b = e.a, e.b
            na = self.graph.nodes[a]
            nb = self.graph.nodes[b]
            line_id = self.canvas.create_line(na.x, na.y, nb.x, nb.y, width=EDGE_LINE_WIDTH, fill=self._edge_color(e))
            # compute label position mid-point slightly offset
            mx = (na.x + nb.x) / 2
            my = (na.y + nb.y) / 2
            label = f"{e.distance}/{e.time}{' A' if not e.accessible else ''}"
            label_id = self.canvas.create_text(mx, my - 12, text=label, font=("TkDefaultFont", 8), fill="gray30")
            e.line_id = line_id
            e.label_id = label_id
        # draw nodes on top
        for node in self.graph.nodes.values():
            self._draw_node(node)

    def _edge_color(self, e: Edge):
        if e.closed:
            return COLOR_CLOSED
        if not e.accessible:
            return COLOR_NONACCESS
        return COLOR_REGULAR

    def _node_at_point(self, x, y):
        # return node name if point within node radius
        for name, node in self.graph.nodes.items():
            dx = node.x - x
            dy = node.y - y
            if dx*dx + dy*dy <= NODE_RADIUS*NODE_RADIUS:
                return name
        return None

    def _edge_at_point(self, x, y):
        # find edge whose line is near (distance to segment small)
        threshold = 6
        for k, e in self.graph.edges.items():
            a, b = e.a, e.b
            na = self.graph.nodes[a]
            nb = self.graph.nodes[b]
            if point_near_segment(x, y, na.x, na.y, nb.x, nb.y, threshold):
                return (a, b, e)
        return None

    def on_randomize(self, _=None):
        if not self.graph.edges:
            messagebox.showinfo("No edges", "There are no edges to randomize.")
            return
        self.graph.randomize_weights(1, 200)
        self._redraw_all()
        self.info_label.config(text="Randomized all edge distances/times.")

    def toggle_selected_edge_closed(self):
        if not self.selected_edge:
            messagebox.showinfo("No edge selected", "Select an edge first (enable Edge Select and right-click an edge).")
            return
        a, b = self.selected_edge
        e = self.graph.get_edge(a, b)
        if not e:
            messagebox.showerror("Edge missing", "Selected edge no longer exists.")
            self.selected_edge = None
            self.edge_label.config(text="None")
            return
        e.closed = not e.closed
        self.edge_label.config(text=f"{a} ↔ {b} | dist={e.distance} time={e.time} acc={'Y' if e.accessible else 'N'} closed={'Y' if e.closed else 'N'}")
        self._redraw_all()

    def toggle_selected_edge_accessible(self):
        if not self.selected_edge:
            messagebox.showinfo("No edge selected", "Select an edge first (enable Edge Select and right-click an edge).")
            return
        a, b = self.selected_edge
        e = self.graph.get_edge(a, b)
        if not e:
            messagebox.showerror("Edge missing", "Selected edge no longer exists.")
            self.selected_edge = None
            self.edge_label.config(text="None")
            return
        e.accessible = not e.accessible
        self.edge_label.config(text=f"{a} ↔ {b} | dist={e.distance} time={e.time} acc={'Y' if e.accessible else 'N'} closed={'Y' if e.closed else 'N'}")
        self._redraw_all()

    def run_search(self, alg="BFS"):
        start = self.start_var.get().strip()
        goal = self.goal_var.get().strip()
        if start == "" or goal == "":
            messagebox.showerror("Invalid input", "Please provide both start and goal building names.")
            return
        if start not in self.graph.nodes:
            messagebox.showerror("Invalid start", f"Start node '{start}' does not exist.")
            return
        if goal not in self.graph.nodes:
            messagebox.showerror("Invalid goal", f"Goal node '{goal}' does not exist.")
            return
        allow_closed = False  # never traverse closed edges
        accessible_only = self.accessible_only.get()
        if alg == "BFS":
            path, visited_order = bfs(self.graph, start, goal, accessible_only=accessible_only, allow_closed=allow_closed)
            if path is None:
                messagebox.showinfo("No Path", f"No path found between {start} and {goal} with current settings.")
                return
            self.info_label.config(text=f"BFS found path {len(path)-1} hops. Traversal shown.")
            self._animate_traversal(visited_order, path)
        else:
            path, visited_order = dfs(self.graph, start, goal, accessible_only=accessible_only, allow_closed=allow_closed)
            if path is None:
                messagebox.showinfo("No Path", f"No path found between {start} and {goal} with current settings.")
                return
            self.info_label.config(text=f"DFS found path {len(path)-1} hops. Traversal shown.")
            self._animate_traversal(visited_order, path)

    def _animate_traversal(self, visited_order, final_path):
        # Cancel any previous animation
        if self._anim_after_id:
            self.root.after_cancel(self._anim_after_id)
            self._anim_after_id = None

        # initial redraw to reset colors
        self._redraw_all()
        # highlight visited sequence, then highlight final path
        steps = []
        for n in visited_order:
            steps.append(("visit_node", n))
        # Wait a bit then highlight final path edges and nodes in green
        for i in range(len(final_path) - 1):
            a, b = final_path[i], final_path[i+1]
            steps.append(("path_edge", a, b))
        # schedule steps
        def do_step(i=0):
            if i >= len(steps):
                # finished, show textual results summary
                summary = f"Final path: {' -> '.join(final_path)} | Hops: {len(final_path)-1}\nTraversal order: {', '.join(visited_order)}"
                messagebox.showinfo("Search Result", summary)
                self._anim_after_id = None
                return
            step = steps[i]
            if step[0] == "visit_node":
                n = step[1]
                node = self.graph.nodes.get(n)
                if node:
                    # draw visited overlay circle
                    self.canvas.create_oval(node.x - NODE_RADIUS+2, node.y - NODE_RADIUS+2, node.x + NODE_RADIUS-2, node.y + NODE_RADIUS-2, fill=COLOR_VISITED, stipple='gray50', outline="")
            elif step[0] == "path_edge":
                a, b = step[1], step[2]
                e = self.graph.get_edge(a, b)
                if e:
                    # recolor edge to path color and redraw label
                    self.canvas.itemconfig(e.line_id, fill=COLOR_PATH, width=EDGE_LINE_WIDTH+1)
                    # also color nodes
                    na = self.graph.nodes[a]
                    nb = self.graph.nodes[b]
                    # draw filled circle behind node text
                    self.canvas.create_oval(na.x - NODE_RADIUS+1, na.y - NODE_RADIUS+1, na.x + NODE_RADIUS-1, na.y + NODE_RADIUS-1, fill=COLOR_PATH, outline="")
                    self.canvas.create_oval(nb.x - NODE_RADIUS+1, nb.y - NODE_RADIUS+1, nb.x + NODE_RADIUS-1, nb.y + NODE_RADIUS-1, fill=COLOR_PATH, outline="")
            # schedule next
            self._anim_after_id = self.root.after(self.animation_speed, lambda: do_step(i+1))

        do_step(0)


# Simple dialog to collect edge details
class EdgeDialog:
    def __init__(self, parent, a, b):
        top = self.top = tk.Toplevel(parent)
        top.title(f"Connect {a} ↔ {b}")
        ttk.Label(top, text=f"Connecting {a} ↔ {b}").pack(pady=4)
        f = ttk.Frame(top); f.pack(padx=6, pady=4)
        ttk.Label(f, text="Distance (numeric):").grid(row=0, column=0, sticky=tk.W)
        self.dist_var = tk.StringVar(value="1")
        ttk.Entry(f, textvariable=self.dist_var, width=8).grid(row=0, column=1)
        ttk.Label(f, text="Time (numeric):").grid(row=1, column=0, sticky=tk.W)
        self.time_var = tk.StringVar(value="1")
        ttk.Entry(f, textvariable=self.time_var, width=8).grid(row=1, column=1)
        self.acc_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="Accessible (wheelchair-friendly)", variable=self.acc_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(4,0))

        btnf = ttk.Frame(top)
        btnf.pack(pady=6)
        ttk.Button(btnf, text="OK", command=self.on_ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(btnf, text="Cancel", command=self.on_cancel).pack(side=tk.LEFT)
        self.result = None

    def on_ok(self):
        try:
            d = float(self.dist_var.get())
            t = float(self.time_var.get())
            if d <= 0 or t <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Invalid", "Distance and Time must be positive numbers.")
            return
        self.result = (d, t, self.acc_var.get())
        self.top.destroy()

    def on_cancel(self):
        self.result = None
        self.top.destroy()

# BFS (fewest hops) implementation. Returns (path, visited_order) or (None, visited_order)
def bfs(graph: Graph, start, goal, accessible_only=False, allow_closed=False):
    visited = set()
    q = deque()
    q.append(start)
    parent = {start: None}
    visited_order = []
    visited.add(start)
    while q:
        cur = q.popleft()
        visited_order.append(cur)
        if cur == goal:
            # build path
            path = []
            n = cur
            while n is not None:
                path.append(n)
                n = parent[n]
            path.reverse()
            return path, visited_order
        for nb in graph.neighbors(cur, accessible_only=accessible_only, allow_closed=allow_closed):
            if nb not in visited:
                visited.add(nb)
                parent[nb] = cur
                q.append(nb)
    return None, visited_order

# DFS implementation (non-recursive, returns first found path)
def dfs(graph: Graph, start, goal, accessible_only=False, allow_closed=False):
    visited = set()
    stack = [(start, [start])]
    visited_order = []
    while stack:
        cur, path = stack.pop()
        if cur in visited:
            continue
        visited.add(cur)
        visited_order.append(cur)
        if cur == goal:
            return path, visited_order
        # push neighbors in reversed sorted order for deterministic-ish behavior
        nb_list = list(graph.neighbors(cur, accessible_only=accessible_only, allow_closed=allow_closed))
        nb_list.sort(reverse=True)
        for nb in nb_list:
            if nb not in visited:
                stack.append((nb, path + [nb]))
    return None, visited_order

# geometry helper
def point_near_segment(px, py, x1, y1, x2, y2, threshold):
    # distance from point P to segment AB
    # from: project P onto line AB, clamp to segment, compute distance
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        # segment is a point
        return (px - x1)**2 + (py - y1)**2 <= threshold*threshold
    t = ((px - x1) * dx + (py - y1) * dy) / (dx*dx + dy*dy)
    t = max(0, min(1, t))
    projx = x1 + t * dx
    projy = y1 + t * dy
    dist2 = (px - projx)**2 + (py - projy)**2
    return dist2 <= threshold*threshold

def main():
    root = tk.Tk()
    app = App(root)
    root.geometry("1000x720")
    root.mainloop()

if __name__ == "__main__":
    main()
