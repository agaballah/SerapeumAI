# -*- coding: utf-8 -*-
import math
import random
import tkinter as tk
import customtkinter as ctk
from typing import Dict, List, Any, Optional

from src.domain.intelligence.truth_graph import TruthGraphService

class TruthMapPage(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.nodes = {} # id -> {x, y, vx, vy, color, label, type}
        self.links = [] # {from, to, type, confidence}
        self.selected_node = None
        
        self._build_ui()
        
    def _build_ui(self):
        # Header
        self.header = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#2b2b2b")
        self.header.grid(row=0, column=0, sticky="ew")
        
        self.lbl_title = ctk.CTkLabel(self.header, text="🌐 Project Truth Map", font=("Arial", 20, "bold"))
        self.lbl_title.pack(side="left", padx=20, pady=10)
        
        self.btn_refresh = ctk.CTkButton(self.header, text="🔄 Refresh Graph", width=120, command=self.on_show)
        self.btn_refresh.pack(side="right", padx=20, pady=10)
        
        # Main Canvas Area
        self.canvas_frame = ctk.CTkFrame(self, fg_color="#1e1e1e")
        self.canvas_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Controls / Info Panel (Overlay or Side)
        self.info_panel = ctk.CTkFrame(self.canvas_frame, width=250, fg_color="#252525", corner_radius=10)
        self.info_panel.place(relx=1.0, rely=0.0, anchor="ne", padx=20, pady=20)
        
        self.lbl_info = ctk.CTkLabel(self.info_panel, text="Selection Info", font=("Arial", 14, "bold"))
        self.lbl_info.pack(pady=10, padx=10)
        
        self.txt_details = ctk.CTkTextbox(self.info_panel, height=150, width=220)
        self.txt_details.pack(pady=5, padx=10)
        self.txt_details.insert("1.0", "Click a node to view relationships and confidence tiers.")
        self.txt_details.configure(state="disabled")

        # Events
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

    def on_show(self):
        if not self.controller.db:
            return
        
        self._load_graph_data()
        self._initialize_layout()
        self._animate()

    def _load_graph_data(self):
        service = TruthGraphService(self.controller.db)
        
        # Fetch all nodes and links (Simplified for small-medium projects)
        # In a real system, we might paginate or focus on a subset
        try:
            nodes_raw = self.controller.db.execute("SELECT id, entity_type, value FROM entity_nodes LIMIT 100").fetchall()
            links_raw = self.controller.db.execute("SELECT from_entity_id, to_entity_id, rel_type, confidence_tier FROM entity_links LIMIT 200").fetchall()
            
            self.nodes = {}
            for row in nodes_raw:
                n = dict(row)
                self.nodes[n["id"]] = {
                    "id": n["id"],
                    "type": n["entity_type"],
                    "value": n["value"],
                    "x": random.randint(100, 700),
                    "y": random.randint(100, 500),
                    "vx": 0, "vy": 0,
                    "color": self._get_color(n["entity_type"]),
                    "radius": 12 if n["entity_type"] in ["activity", "element"] else 8
                }
                
            self.links = []
            for row in links_raw:
                l = dict(row)
                if l["from_entity_id"] in self.nodes and l["to_entity_id"] in self.nodes:
                    self.links.append(l)
                    
        except Exception as e:
            print(f"Failed to load graph data: {e}")

    def _get_color(self, entity_type: str) -> str:
        colors = {
            "activity": "#3b82f6",     # Blue (Schedule)
            "element": "#10b981",      # Green (BIM)
            "drawing": "#f59e0b",      # Orange (Docs)
            "document": "#f59e0b",
            "fact": "#ef4444",         # Red (Verified Facts)
            "wbs": "#8b5cf6",          # Purple
            "zone": "#06b6d4"          # Cyan
        }
        return colors.get(entity_type, "#94a3b8") # Slate default

    def _initialize_layout(self):
        # Center nodes initially
        w = self.canvas.winfo_width() or 800
        h = self.canvas.winfo_height() or 600
        for n in self.nodes.values():
            n["x"] = w/2 + random.uniform(-100, 100)
            n["y"] = h/2 + random.uniform(-100, 100)

    def _animate(self):
        # Simple Force-Directed Layout
        # 1. Repulsion (between all nodes)
        # 2. Attraction (between linked nodes)
        # 3. Centering
        
        K = 100 # Ideal link distance
        iterations = 50 # Run a few steps
        
        for _ in range(iterations):
            # Repulsion
            for id1, n1 in self.nodes.items():
                for id2, n2 in self.nodes.items():
                    if id1 == id2: continue
                    dx = n1["x"] - n2["x"]
                    dy = n1["y"] - n2["y"]
                    dist_sq = dx*dx + dy*dy + 0.01
                    dist = math.sqrt(dist_sq)
                    force = 2000 / dist_sq
                    n1["vx"] += (dx/dist) * force
                    n1["vy"] += (dy/dist) * force
            
            # Attraction
            for l in self.links:
                n1 = self.nodes[l["from_entity_id"]]
                n2 = self.nodes[l["to_entity_id"]]
                dx = n1["x"] - n2["x"]
                dy = n1["y"] - n2["y"]
                dist = math.sqrt(dx*dx + dy*dy) + 0.01
                force = (dist - K) * 0.05
                n1["vx"] -= (dx/dist) * force
                n1["vy"] -= (dy/dist) * force
                n2["vx"] += (dx/dist) * force
                n2["vy"] += (dy/dist) * force
            
            # Apply velocities and friction
            for n in self.nodes.values():
                n["x"] += n["vx"]
                n["y"] += n["vy"]
                n["vx"] *= 0.8
                n["vy"] *= 0.8
        
        self.render()

    def render(self):
        self.canvas.delete("all")
        
        # Draw Links
        for l in self.links:
            n1 = self.nodes[l["from_entity_id"]]
            n2 = self.nodes[l["to_entity_id"]]
            color = "#4a4a4a"
            if l["confidence_tier"] == "AUTO_VALIDATED":
                 color = "#3b82f6" # Highlight validated links
            
            self.canvas.create_line(n1["x"], n1["y"], n2["x"], n2["y"], fill=color, width=1)
            
        # Draw Nodes
        for n in self.nodes.values():
            r = n["radius"]
            color = n["color"]
            outline = "#ffffff" if n == self.selected_node else "#1a1a1a"
            
            self.canvas.create_oval(
                n["x"] - r, n["y"] - r, n["x"] + r, n["y"] + r,
                fill=color, outline=outline, width=2, tags=("node", n["id"])
            )
            
            # Label for important nodes
            if n["radius"] > 10 or n == self.selected_node:
                self.canvas.create_text(n["x"], n["y"] + r + 10, text=n["value"], fill="#cccccc", font=("Arial", 8))

    def _on_canvas_click(self, event):
        item = self.canvas.find_closest(event.x, event.y)
        tags = self.canvas.gettags(item)
        if "node" in tags:
            node_id = int(tags[1])
            self.selected_node = self.nodes.get(node_id)
            self._update_info()
            self.render()
        else:
            self.selected_node = None
            self._update_info()
            self.render()

    def _update_info(self):
        self.txt_details.configure(state="normal")
        self.txt_details.delete("1.0", "end")
        
        if self.selected_node:
            n = self.selected_node
            info = f"Entity: {n['value']}\nType: {n['type'].upper()}\n\n"
            
            # Fetch neighbors from TruthGraphService
            service = TruthGraphService(self.controller.db)
            neighbors = service.get_neighbors(n["id"])
            
            info += f"Links ({len(neighbors)}):\n"
            for nb in neighbors:
                info += f"- {nb['rel_type']} -> {nb['value']} [{nb['confidence_tier']}]\n"
            
            self.txt_details.insert("1.0", info)
        else:
            self.txt_details.insert("1.0", "Click a node to view relationships and confidence tiers.")
            
        self.txt_details.configure(state="disabled")

    def _on_canvas_drag(self, event):
        # Implementation for panning could be added here
        pass

    def _on_mousewheel(self, event):
        # Implementation for zooming could be added here
        pass
