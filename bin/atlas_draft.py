"""Grid drafter for the atlas flowcharts.

The `.mmd` file stays the only source of nodes, labels, edges, kinds, and groups. A sidecar
`layout:` block only places nodes on `[column, row]` cells and may add routing hints. Edges are
routed orthogonally through the gutters between columns; edges that share an endpoint and a
gutter share a trunk. Output is static SVG with no script and no remote reference.
"""

from __future__ import annotations

import html
import re

ID = r"[A-Za-z_](?:\w|-(?![-.>]))*"
EDGE_START_RE = re.compile(rf"^\s*({ID})")
EDGE_HOP_RE = re.compile(rf'\s*(<?)(=+>|-\.+->|-{{2,}}>)\s*(?:\|"?(.*?)"?\|)?\s*({ID})')
NODE_RE = re.compile(rf'^\s*({ID})\s*\["(.*)"\]\s*$')
SUBGRAPH_RE = re.compile(r'^\s*subgraph\s+([^\["]+?)\s*(?:\["(.*)"\])?\s*$')
CLASS_RE = re.compile(r"^\s*class\s+([\w,-]+)\s+(\w+)\s*$")
HEADER_RE = re.compile(r"^\s*flowchart\s+(LR|RL|TD|TB|BT)\s*$")
DIRECTION_RE = re.compile(r"^\s*direction\s+(LR|RL|TD|TB|BT)\s*$")
INVISIBLE_RE = re.compile(rf"^\s*{ID}(?:\s*~~~\s*{ID})+\s*$")
ARROWISH = re.compile(r"=+>|-{2,}>|-\.+->|~~~")
TAG_RE = re.compile(r"</?(?:div|span|b|i|em|strong|small|code|sub|sup|u|img)\b[^<>]*>", re.I)

# Rough advance widths (px) used to fit text: node name, node sub-line, edge label, zone title.
NAME_PX, SUB_PX, LABEL_PX, ZONE_PX = 7.0, 5.9, 6.1, 6.3
LANES = (0, 9, -9, 18, -18, 27, -27)
SIDES = ("l", "r", "t", "b")


class DraftError(ValueError):
    pass


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def label_lines(raw: str) -> tuple[list[str], str | None]:
    """Visible text lines of a node or edge label, and the embedded icon path if any.

    Only real markup tags are removed, so text such as `a < b > c` survives.
    """
    icon = re.search(r"<img[^>]*\bsrc='([^']+)'", raw)
    text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
    text = re.sub(r"#(\w+);", lambda m: f"&{m.group(1)};", TAG_RE.sub("", text))
    text = html.unescape(text)
    lines = [" ".join(line.split()) for line in text.split("\n")]
    return [line for line in lines if line], icon.group(1) if icon else None


def parse_edges(line: str) -> list[dict] | None:
    """One edge statement, possibly a chain `a --> b ==>|x| c`, as a list of edges."""
    start = EDGE_START_RE.match(line)
    if not start:
        return None
    pos, a, edges = start.end(), start.group(1), []
    while pos < len(line):
        hop = EDGE_HOP_RE.match(line, pos)
        if not hop:
            return None
        back, op, label, b = hop.groups()
        kind = "p" if op.startswith("=") else "c" if "." in op else "d"
        lines, _ = label_lines(label or "")
        edges.append({"a": a, "b": b, "kind": kind, "label": lines, "both": bool(back)})
        pos, a = hop.end(), b
    return edges or None


def parse_flowchart(text: str) -> dict:
    """Parse the repo's flowchart subset. Unknown edge syntax fails instead of being dropped.

    The declared direction is recorded but not used: the layout block places every node.
    Invisible `~~~` links only steer Mermaid's layout, so they are skipped.
    """
    nodes, groups, edges, classes, stack = {}, [], [], {}, []
    header = None
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        if header is None:
            match = HEADER_RE.match(stripped)
            if not match:
                raise DraftError(f"line {lineno}: not a flowchart: {stripped!r}")
            header = match.group(1)
            continue
        if stripped.startswith(("classDef ", "style ", "linkStyle ")):
            continue
        if INVISIBLE_RE.match(stripped) or DIRECTION_RE.match(stripped):
            continue
        if match := SUBGRAPH_RE.match(stripped):
            title, _ = label_lines(match.group(2) if match.group(2) is not None else match.group(1))
            group = {
                "id": match.group(1),
                "title": " ".join(title),
                "members": [],
                "parent": stack[-1]["id"] if stack else None,
            }
            groups.append(group)
            stack.append(group)
            continue
        if stripped == "end":
            if not stack:
                raise DraftError(f"line {lineno}: unmatched end")
            stack.pop()
            continue
        if match := CLASS_RE.match(stripped):
            for node_id in match.group(1).split(","):
                classes[node_id] = match.group(2)
            continue
        if match := NODE_RE.match(stripped):
            lines, icon = label_lines(match.group(2))
            if not lines:
                raise DraftError(f"line {lineno}: node {match.group(1)!r} has no visible label")
            if match.group(1) in nodes:
                raise DraftError(f"line {lineno}: node {match.group(1)!r} is declared twice")
            nodes[match.group(1)] = {"id": match.group(1), "lines": lines, "icon": icon}
            for group in stack:
                group["members"].append(match.group(1))
            continue
        if ARROWISH.search(stripped) and (chain := parse_edges(stripped)):
            edges.extend(chain)
            continue
        if ARROWISH.search(stripped):
            raise DraftError(f"line {lineno}: unsupported edge syntax: {stripped!r}")
        raise DraftError(f"line {lineno}: unsupported statement: {stripped!r}")
    if header is None:
        raise DraftError("empty source: no flowchart header")
    if stack:
        raise DraftError(f"subgraph {stack[-1]['id']!r} is never closed")
    group_ids = {g["id"] for g in groups}
    for edge in edges:
        for end in (edge["a"], edge["b"]):
            if end not in nodes and end not in group_ids:
                raise DraftError(f"edge endpoint {end!r} has no node or subgraph declaration")
    for node_id, node in nodes.items():
        node["cls"] = classes.get(node_id, "")
    return {"direction": header, "nodes": nodes, "groups": groups, "edges": edges}


def wrap(line: str, limit: int) -> list[str]:
    out, cur = [], ""
    for word in line.split(" "):
        if cur and len(cur) + 1 + len(word) > limit:
            out.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}" if cur else word
    out.append(cur)
    return out


def _is_port(value: object) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and value[0] in SIDES
        and isinstance(value[1], (int, float))
    )


class Sheet:
    def __init__(
        self,
        flow: dict,
        layout: dict,
        stores: set[str] | None = None,
        icons: set[str] | None = None,
    ):
        if not isinstance(layout, dict):
            raise DraftError("layout must be a mapping")
        grid = layout.get("grid") or {}
        self.cw = grid.get("column", 236)
        self.nw = grid.get("node_width", 176)
        self.rh = grid.get("row", 100)
        self.px, self.py = 28, 40
        self.colshift = {int(k): v for k, v in (layout.get("column_shift") or {}).items()}
        self.flow, self.stores, self.key = flow, stores or set(), set(layout.get("key") or [])
        unknown_keys = sorted(self.key - set(flow["nodes"]))
        if unknown_keys:
            raise DraftError(f"layout.key names unknown nodes: {unknown_keys}")
        positions = layout.get("nodes") or {}
        if not isinstance(positions, dict):
            raise DraftError("layout.nodes must map node ids to [column, row]")
        for node_id, pos in positions.items():
            if not (
                isinstance(pos, (list, tuple))
                and len(pos) == 2
                and all(isinstance(v, (int, float)) for v in pos)
            ):
                raise DraftError(f"layout.nodes.{node_id} must be [column, row], got {pos!r}")
        missing = sorted(set(flow["nodes"]) - set(positions))
        extra = sorted(set(positions) - set(flow["nodes"]))
        if missing or extra:
            raise DraftError(f"layout mismatch: missing {missing}, unknown {extra}")
        if icons is not None:
            for node in flow["nodes"].values():
                if node["icon"] and node["icon"] not in icons:
                    raise DraftError(f"node {node['id']!r} icon is not a verified asset")
        self.nodes = {
            node_id: self._box(flow["nodes"][node_id], *positions[node_id])
            for node_id in flow["nodes"]
        }
        hints_list = layout.get("edges") or []
        for h in hints_list:
            if not isinstance(h, dict) or "from" not in h or "to" not in h:
                raise DraftError(f"layout.edges entries need from and to: {h!r}")
            for key in ("source_port", "target_port"):
                if h.get(key) is not None and not _is_port(h[key]):
                    raise DraftError(
                        f"layout.edges {h['from']}>{h['to']} {key} must be [l|r|t|b, offset]"
                    )
        declared = [f"{e['a']}>{e['b']}" for e in flow["edges"]]
        unknown = sorted({f"{h['from']}>{h['to']}" for h in hints_list} - set(declared))
        if unknown:
            raise DraftError(f"layout edge hints name no edge: {unknown}")
        # Repeated a>b edges take their hints in order: the nth hint for a pair applies to the
        # nth declared edge for that pair, so parallel duplicates can get separate ports.
        queues: dict[str, list[dict]] = {}
        for h in hints_list:
            queues.setdefault(f"{h['from']}>{h['to']}", []).append(h)
        self.edges = []
        seen: dict[tuple[str, str], int] = {}
        for i, e in enumerate(flow["edges"]):
            pair = f"{e['a']}>{e['b']}"
            hint = queues[pair].pop(0) if queues.get(pair) else {}
            k = seen[(e["a"], e["b"])] = seen.get((e["a"], e["b"]), -1) + 1
            # Unhinted repeats run in parallel 12px apart instead of on top of each other.
            parallel = (k + 1) // 2 * 12 * (1 if k % 2 else -1)
            self.edges.append(dict(e, hint=hint, index=i, parallel=parallel))
        bottom = set(layout.get("zone_titles_below") or [])
        unknown_zones = sorted(bottom - {g["id"] for g in flow["groups"]})
        if unknown_zones:
            raise DraftError(f"layout.zone_titles_below names unknown groups: {unknown_zones}")
        # Children first, so a parent frame encloses its nested frames and their titles.
        built: dict[str, dict] = {}
        for g in reversed(flow["groups"]):
            if g["members"]:
                kids = [
                    built[c["id"]]
                    for c in flow["groups"]
                    if c["parent"] == g["id"] and c["id"] in built
                ]
                built[g["id"]] = self._zone(g, g["id"] in bottom, kids)
        self.zones = [built[g["id"]] for g in flow["groups"] if g["id"] in built]
        # Edge endpoints are nodes or, as in Mermaid, whole subgraphs (drawn to the zone frame).
        self.ends = dict(self.nodes)
        zones = {z["id"]: z for z in self.zones}
        for e in self.edges:
            for end in (e["a"], e["b"]):
                if end in self.nodes or end in self.ends:
                    continue
                if end not in zones:
                    raise DraftError(f"edge endpoint {end!r} is an empty subgraph")
                cols = [self.nodes[m]["col"] for m in zones[end]["members"]]
                self.ends[end] = dict(zones[end], col=min(cols), colmax=max(cols))
        self.routed = False

    def _box(self, node: dict, col: float, row: float) -> dict:
        w = self.nw
        names = wrap(node["lines"][0], int((w - 14) / NAME_PX))
        subs = [p for line in node["lines"][1:] for p in wrap(line, int((w - 14) / SUB_PX))]
        h = (62 if node["icon"] else 14) + 17 * len(names) + 14 * len(subs) + 8
        if node["id"] in self.stores:
            h += 12
        x = self.px + col * self.cw + sum(v for k, v in self.colshift.items() if col >= k)
        return {
            "id": node["id"],
            "col": col,
            "colmax": col,
            "x": x,
            "y": self.py + row * self.rh - h / 2,
            "w": w,
            "h": h,
            "names": names,
            "subs": subs,
            "icon": node["icon"],
            "cls": node["cls"],
        }

    @staticmethod
    def title_boxes(z: dict) -> list[dict]:
        n = len(z["title"])
        out = []
        for i, line in enumerate(z["title"]):
            if z["below"]:
                ty = z["y"] + z["h"] - 8 - 14 * (n - 1 - i)
            else:
                ty = z["y"] + 16 + 14 * i
            out.append(
                {
                    "x": z["x"] + 7,
                    "y": ty - 11,
                    "w": len(line) * ZONE_PX + 8,
                    "h": 15,
                    "ty": ty,
                    "line": line,
                }
            )
        return out

    def _zone(self, group: dict, below: bool, kids: list[dict] | None = None) -> dict:
        boxes = [self.nodes[m] for m in group["members"]] + [
            {"x": k["x"] - 2, "y": k["y"] - 2, "w": k["w"] + 4, "h": k["h"] + 4} for k in kids or []
        ]
        x0 = min(b["x"] for b in boxes) - 14
        x1 = max(b["x"] + b["w"] for b in boxes) + 14
        title = wrap(group["title"], max(8, int((x1 - x0 - 16) / ZONE_PX)))
        head = 10 + 14 * len(title)
        top = min(b["y"] for b in boxes) - (14 if below else 14 + head)
        bot = max(b["y"] + b["h"] for b in boxes) + (14 + head if below else 14)
        return {
            "id": group["id"],
            "title": title,
            "below": below,
            "x": x0,
            "y": top,
            "w": x1 - x0,
            "h": bot - top,
            "members": set(group["members"]),
        }

    # ------------------------------------------------------------ geometry helpers
    def columns(self) -> list[float]:
        return sorted({n["col"] for n in self.nodes.values()})

    def rank_hi(self, c):
        return max(n["x"] + n["w"] for n in self.nodes.values() if n["col"] == c)

    def rank_lo(self, c):
        return min(n["x"] for n in self.nodes.values() if n["col"] == c)

    def gutter(self, c):
        nxt = min(x for x in self.columns() if x > c)
        return (self.rank_hi(c) + self.rank_lo(nxt)) / 2

    def prev_col(self, c):
        return max(x for x in self.columns() if x < c)

    def blocked(self, xa, xb, y, skip):
        lo, hi = min(xa, xb), max(xa, xb)
        return any(
            n["x"] < hi - 1 and n["x"] + n["w"] > lo + 1 and n["y"] - 7 < y < n["y"] + n["h"] + 7
            for n in self.nodes.values()
            if n["id"] not in skip
        )

    def vblocked(self, x, ya, yb, skip):
        lo, hi = min(ya, yb), max(ya, yb)
        return any(
            n["x"] - 5 < x < n["x"] + n["w"] + 5 and n["y"] < hi - 1 and n["y"] + n["h"] > lo + 1
            for n in self.nodes.values()
            if n["id"] not in skip
        )

    @staticmethod
    def port(b, side, off=0):
        """Port on a box side, shifted along that side by `off`."""
        cx, cy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
        return {
            "l": (b["x"], cy + off),
            "r": (b["x"] + b["w"], cy + off),
            "t": (cx + off, b["y"]),
            "b": (cx + off, b["y"] + b["h"]),
        }[side]

    # ------------------------------------------------------------ routing
    def route(self):
        if self.routed:
            return
        lanes, outs, ins = {}, {}, {}

        def lane(g, key):
            used = lanes.setdefault(g, {})
            if key not in used:
                if len(used) >= len(LANES):
                    raise DraftError(
                        f"more than {len(LANES)} trunks in the gutter after column {g}; "
                        "spread the layout"
                    )
                used[key] = LANES[len(used)]
            return used[key]

        for ed in self.edges:
            a, b, hint = self.ends[ed["a"]], self.ends[ed["b"]], ed["hint"]
            explicit = hint.get("via") or (hint.get("source_port") or ("r",))[0] in "tb"
            if explicit:
                continue
            if b["col"] > a["colmax"]:
                fwd, ga, gb = True, a["colmax"], self.prev_col(b["col"])
            elif b["colmax"] < a["col"]:
                fwd, ga, gb = False, self.prev_col(a["col"]), b["colmax"]
            else:
                continue
            ed["_g"] = (ga, gb, fwd)
            outs.setdefault((ed["a"], ga), []).append(ed)
            ins.setdefault((ed["b"], gb), []).append(ed)
        for ed in self.edges:
            ed["pts"] = self._route_one(ed, outs, ins, lane)
        for ed in self.edges:
            ed["pts"] = clean(ed["pts"])
        self.routed = True

    def _route_one(self, ed, outs, ins, lane):
        a, b, hint = self.ends[ed["a"]], self.ends[ed["b"]], ed["hint"]
        sp_hint, tp_hint = hint.get("source_port"), hint.get("target_port")
        if hint.get("via") or (sp_hint and sp_hint[0] in "tb"):
            sp = self.port(a, *(sp_hint or ("r", 0)))
            tp = self.port(b, *(tp_hint or ("l", 0)))
            via = hint.get("via") or []
            mid = [(sp[0] if vx is None else vx, tp[1] if vy is None else vy) for vx, vy in via]
            if not via:  # a t/b port without waypoints drops straight, then turns to the target
                mid = [(sp[0], tp[1])]
            return [sp, *mid, tp]
        ay = a["y"] + a["h"] / 2 + (sp_hint[1] if sp_hint else ed["parallel"])
        by = b["y"] + b["h"] / 2 + (tp_hint[1] if tp_hint else ed["parallel"])
        if "_g" not in ed:  # same column: straight down or up between the boxes
            down = b["y"] > a["y"]
            ax, bx = a["x"] + a["w"] / 2, b["x"] + b["w"] / 2
            y1, y2 = a["y"] + (a["h"] if down else 0), b["y"] + (0 if down else b["h"])
            if abs(ax - bx) < 2:
                return [(ax, y1), (bx, y2)]
            return [(ax, y1), (ax, (y1 + y2) / 2), (bx, (y1 + y2) / 2), (bx, y2)]
        ga, gb, fwd = ed["_g"]
        sx, tx = (a["x"] + a["w"], b["x"]) if fwd else (a["x"], b["x"] + b["w"])
        skip = {ed["a"], ed["b"]}
        if abs(ay - by) < 1 and not self.blocked(sx, tx, ay, skip):
            return [(sx, ay), (tx, by)]
        fan_out, fan_in = len(outs[(ed["a"], ga)]) > 1, len(ins[(ed["b"], gb)]) > 1
        own = ("e", ed["index"])
        if ga == gb:
            key = ("t", ed["b"]) if fan_in else ("s", ed["a"]) if fan_out else own
            x1 = x2 = self.gutter(ga) + lane(ga, key)
        else:
            # Edges converging on one target merge into its trunk already in the first gutter.
            first = ("s", ed["a"]) if fan_out else ("t", ed["b"]) if fan_in else own
            x1 = self.gutter(ga) + lane(ga, first)
            x2 = self.gutter(gb) + lane(gb, ("t", ed["b"]) if fan_in else own)
        if abs(x1 - x2) < 1:
            return [(sx, ay), (x1, ay), (x1, by), (tx, by)]
        cy = self._crossing(x1, x2, ay, by, skip)
        return [(sx, ay), (x1, ay), (x1, cy), (x2, cy), (x2, by), (tx, by)]

    def _crossing(self, x1, x2, ay, by, skip):
        def ok(y):
            return (
                not self.blocked(x1, x2, y, skip)
                and not self.vblocked(x1, ay, y, skip)
                and not self.vblocked(x2, y, by, skip)
            )

        for dy in range(0, int(self.rh * 4), 6):
            for base in (by, ay):
                for cand in (base + dy, base - dy) if dy else (base,):
                    if ok(cand):
                        return cand
        return by

    # ------------------------------------------------------------ labels
    def place_labels(self):
        shared = {}  # segments that lie on another edge's line (a shared trunk) carry no label
        for ed in self.edges:
            others = [s for f in self.edges if f is not ed for s in _segments(f)]
            shared[ed["index"]] = [
                s for s in _segments(ed) if any(_collinear(s, t) for t in others)
            ]
        placed: list[dict] = []
        for ed in self.edges:
            ed["label_box"] = None
            if not ed["label"]:
                continue
            pts = ed["pts"]
            segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
            horiz = [s for s in segs if abs(s[0][1] - s[1][1]) < 0.5]
            at = ed["hint"].get("label_at")
            if at == "first" and horiz:
                order = [horiz[0]]
            elif at == "last" and horiz:
                order = [horiz[-1]]
            else:
                free = [s for s in horiz if s not in shared[ed["index"]]]
                # Longest free horizontal run first (ties go to the run nearest the target),
                # then the edge's own vertical runs, and a shared trunk only as a last resort:
                # a label there would read as belonging to every edge on it.
                own = [s for s in segs if s not in shared[ed["index"]]]
                order = sorted(reversed(free), key=_length, reverse=True)
                order += sorted((s for s in own if s not in horiz), key=_length, reverse=True)
                order += sorted((s for s in segs if s not in own), key=_length, reverse=True)
            first = None
            for seg in order:
                room = max(_length(seg) - 10, 60) if seg in horiz else 150
                limit = max(6, int(room / LABEL_PX))
                lines = [p for line in ed["label"] for p in wrap(line, limit)]
                w = max(len(line) for line in lines) * LABEL_PX + 10
                h = 14 * len(lines) + 2
                box, clear = self._slide_label(ed, seg, w, h, lines, placed)
                first = first or box
                if clear:
                    break
            ed["label_box"] = box if clear else first
            placed.append(ed["label_box"])

    def _slide_label(self, ed, seg, w, h, lines, placed):
        """Centre the label on its run, sliding along it until it clears foreign lines, boxes,
        and earlier labels. Falls back to the centre, where the geometry gate reports it."""
        (x0, y0), (x1, y1) = seg
        horizontal = abs(y0 - y1) < 0.5
        span = abs(x1 - x0) if horizontal else abs(y1 - y0)
        room = max(0.0, (span - (w if horizontal else h)) / 2 - 4)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        own = _segments(ed)
        foreign = [
            t
            for f in self.edges
            if f is not ed
            for t in _segments(f)
            if not any(_collinear(t, o) for o in own)
        ]
        offsets = [0.0]
        step = 6.0
        while step <= room:
            offsets += [step, -step]
            step += 6.0
        for off in offsets:
            px, py = (cx + off, cy) if horizontal else (cx, cy + off)
            box = {"x": px - w / 2, "y": py - h / 2, "w": w, "h": h, "lines": lines}
            if any(_box_hits_segment(box, t) for t in foreign):
                continue
            if any(_boxes_overlap(box, n) for n in self.nodes.values()):
                continue
            if any(_boxes_overlap(box, other) for other in placed):
                continue
            return box, True
        return {"x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h, "lines": lines}, False

    def plan(self) -> Sheet:
        self.route()
        self.place_labels()
        return self

    # ------------------------------------------------------------ output
    def svg(self, diagram_id: str, title: str) -> str:
        self.plan()
        labels = [e["label_box"] for e in self.edges if e["label_box"]]
        boxes = list(self.nodes.values()) + self.zones + labels
        xs = [p[0] for e in self.edges for p in e["pts"]]
        xs += [b["x"] for b in boxes] + [b["x"] + b["w"] for b in boxes]
        ys = [p[1] for e in self.edges for p in e["pts"]]
        ys += [b["y"] for b in boxes] + [b["y"] + b["h"] for b in boxes]
        x0, y0, x1, y1 = min(xs) - 12, min(ys) - 12, max(xs) + 12, max(ys) + 12
        width, height = x1 - x0, y1 - y0
        mid = f"ad-{re.sub(r'[^a-z0-9-]', '-', diagram_id.lower())}"
        markers = "".join(
            f'<marker id="{mid}-{k}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="{w}" markerHeight="{w}" orient="auto-start-reverse" '
            f'markerUnits="userSpaceOnUse"><path class="ad-head ad-{k}" d="M0,0 L10,5 L0,10 z"/>'
            "</marker>"
            for k, w in (("p", 8), ("d", 7), ("c", 7))
        )
        out = [
            f'<svg class="atlas-draft" data-diagram="{esc(diagram_id)}" '
            f'viewBox="{x0:.0f} {y0:.0f} {width:.0f} {height:.0f}" '
            f'width="{width:.0f}" height="{height:.0f}" role="img" aria-label="{esc(title)}" '
            'xmlns="http://www.w3.org/2000/svg">',
            f"<defs>{markers}</defs>",
        ]
        for z in self.zones:
            out.append(
                f'<rect class="ad-zone" data-zone="{esc(z["id"])}" x="{z["x"]:.1f}" '
                f'y="{z["y"]:.1f}" width="{z["w"]:.1f}" height="{z["h"]:.1f}" rx="2"/>'
            )
        for ed in self.edges:
            out.append(
                f'<path class="ad-edge ad-{ed["kind"]}" data-edge="{esc(ed["a"])}&gt;'
                f'{esc(ed["b"])}" data-edge-index="{ed["index"]}" data-kind="{ed["kind"]}" '
                f'd="{path_d(ed["pts"])}" marker-end="url(#{mid}-{ed["kind"]})"'
                + (
                    f' marker-start="url(#{mid}-{ed["kind"]})" data-dir="both"'
                    if ed["both"]
                    else ""
                )
                + "/>"
            )
        for z in self.zones:
            for t in self.title_boxes(z):
                out.append(
                    f'<rect class="ad-knock" x="{t["x"]:.1f}" y="{t["y"]:.1f}" '
                    f'width="{t["w"]:.1f}" height="15"/><text class="ad-zone-title" '
                    f'data-zone-title="{esc(z["id"])}" x="{z["x"] + 11:.1f}" '
                    f'y="{t["ty"]:.1f}">{esc(t["line"])}</text>'
                )
        for n in self.nodes.values():
            out.append(self.node_svg(n))
        for ed in self.edges:
            lb = ed["label_box"]
            if not lb:
                continue
            spans = "".join(
                f'<tspan x="{lb["x"] + lb["w"] / 2:.1f}" y="{lb["y"] + 12 + 14 * i:.1f}">'
                f"{esc(line)}</tspan>"
                for i, line in enumerate(lb["lines"])
            )
            out.append(
                f'<g class="ad-label" data-edge-label="{esc(ed["a"])}&gt;{esc(ed["b"])}" '
                f'data-edge-index="{ed["index"]}"><rect class="ad-knock" x="{lb["x"]:.1f}" '
                f'y="{lb["y"]:.1f}" width="{lb["w"]:.1f}" height="{lb["h"]:.1f}" rx="2"/>'
                f'<text text-anchor="middle">{spans}</text></g>'
            )
        out.append("</svg>")
        return "".join(out)

    def node_svg(self, n: dict) -> str:
        x, y, w, h, cx = n["x"], n["y"], n["w"], n["h"], n["x"] + n["w"] / 2
        parts = [f'<g class="ad-node cls-{esc(n["cls"] or "none")}" data-node="{esc(n["id"])}">']
        if n["id"] in self.key:
            parts.append(
                f'<rect class="ad-key" x="{x - 5:.1f}" y="{y - 5:.1f}" width="{w + 10:.1f}" '
                f'height="{h + 10:.1f}" rx="4"/>'
            )
        if n["id"] in self.stores:
            ry = 7
            parts.append(
                f'<path class="ad-box" d="M{x:.1f},{y + ry:.1f} v{h - 2 * ry:.1f} '
                f'a{w / 2:.1f},{ry} 0 0 0 {w:.1f},0 v{-(h - 2 * ry):.1f}"/>'
                f'<ellipse class="ad-box" cx="{cx:.1f}" cy="{y + ry:.1f}" rx="{w / 2:.1f}" '
                f'ry="{ry}"/>'
            )
            top = y + 12
        else:
            parts.append(
                f'<rect class="ad-box" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
                f'height="{h:.1f}" rx="2"/>'
            )
            top = y
        if n["icon"]:
            parts.append(
                f'<rect class="ad-chip" x="{cx - 21:.1f}" y="{top + 8:.1f}" width="42" '
                f'height="42" rx="2"/><image href="{esc(n["icon"])}" x="{cx - 18:.1f}" '
                f'y="{top + 11:.1f}" width="36" height="36" preserveAspectRatio="xMidYMid meet"/>'
            )
            ty = top + 62 + 13
        else:
            ty = top + 14 + 13
        for i, line in enumerate(n["names"]):
            parts.append(
                f'<text class="ad-name" x="{cx:.1f}" y="{ty + 17 * i:.1f}" text-anchor="middle">'
                f"{esc(line)}</text>"
            )
        ty += 17 * (len(n["names"]) - 1)
        for i, line in enumerate(n["subs"]):
            parts.append(
                f'<text class="ad-sub" x="{cx:.1f}" y="{ty + 15 + 14 * i:.1f}" '
                f'text-anchor="middle">{esc(line)}</text>'
            )
        parts.append("</g>")
        return "".join(parts)


def _length(seg) -> float:
    return abs(seg[1][0] - seg[0][0]) + abs(seg[1][1] - seg[0][1])


def clean(pts):
    out = []
    for p in pts:
        if not out or abs(out[-1][0] - p[0]) >= 0.5 or abs(out[-1][1] - p[1]) >= 0.5:
            out.append(p)
    i = 1
    while i < len(out) - 1:
        a, b, c = out[i - 1], out[i], out[i + 1]
        vertical = abs(a[0] - b[0]) < 0.5 and abs(b[0] - c[0]) < 0.5
        horizontal = abs(a[1] - b[1]) < 0.5 and abs(b[1] - c[1]) < 0.5
        if vertical or horizontal:
            out.pop(i)
        else:
            i += 1
    return out


def path_d(pts, r=9):
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(1, len(pts) - 1):
        (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[i + 1]
        l1, l2 = abs(x1 - x0) + abs(y1 - y0), abs(x2 - x1) + abs(y2 - y1)
        rr = min(r, l1 / 2, l2 / 2)
        ux, uy = ((x1 - x0) / l1, (y1 - y0) / l1) if l1 else (0, 0)
        vx, vy = ((x2 - x1) / l2, (y2 - y1) / l2) if l2 else (0, 0)
        d += (
            f" L{x1 - ux * rr:.1f},{y1 - uy * rr:.1f} "
            f"Q{x1:.1f},{y1:.1f} {x1 + vx * rr:.1f},{y1 + vy * rr:.1f}"
        )
    return d + f" L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"


def plan(
    text: str, layout: dict, stores: set[str] | None = None, icons: set[str] | None = None
) -> Sheet:
    """Parse, place, and route; the returned sheet carries the geometry the tests inspect."""
    return Sheet(parse_flowchart(text), layout, stores, icons).plan()


def draft(
    text: str,
    layout: dict,
    diagram_id: str,
    title: str,
    stores: set[str] | None = None,
    icons: set[str] | None = None,
) -> str:
    return Sheet(parse_flowchart(text), layout, stores, icons).svg(diagram_id, title)


# ---------------------------------------------------------------- geometry gate
def _segments(ed):
    return list(zip(ed["pts"], ed["pts"][1:]))


def _overlap_1d(a0, a1, b0, b1):
    return min(max(a0, a1), max(b0, b1)) - max(min(a0, a1), min(b0, b1))


def _horizontal(seg) -> bool:
    return abs(seg[0][1] - seg[1][1]) < 0.5


def _collinear(s, t):
    """Segment t lies on the same line as s and overlaps it."""
    sh, th = _horizontal(s), _horizontal(t)
    if sh and th:
        return abs(s[0][1] - t[0][1]) < 0.5 and _overlap_1d(s[0][0], s[1][0], t[0][0], t[1][0]) > 1
    if not sh and not th:
        return abs(s[0][0] - t[0][0]) < 0.5 and _overlap_1d(s[0][1], s[1][1], t[0][1], t[1][1]) > 1
    return False


def _box_hits_segment(b, seg, pad=1):
    (ax, ay), (bx, by) = seg
    if _horizontal(seg):
        return (
            b["y"] + pad < ay < b["y"] + b["h"] - pad
            and _overlap_1d(ax, bx, b["x"] + pad, b["x"] + b["w"] - pad) > 0
        )
    return (
        b["x"] + pad < ax < b["x"] + b["w"] - pad
        and _overlap_1d(ay, by, b["y"] + pad, b["y"] + b["h"] - pad) > 0
    )


def _boxes_overlap(a, b):
    return (
        a["x"] < b["x"] + b["w"]
        and a["x"] + a["w"] > b["x"]
        and a["y"] < b["y"] + b["h"]
        and a["y"] + a["h"] > b["y"]
    )


def _inside(px, py, b, m=0):
    return b["x"] + m < px < b["x"] + b["w"] - m and b["y"] + m < py < b["y"] + b["h"] - m


def geometry_findings(sheet: Sheet) -> list[str]:
    """Measure the routed polylines and boxes the SVG is written from.

    Rounded corners cut the polyline only inside a bend, which sits in a gutter. Flags edges
    through foreign boxes, unrelated edges sharing a run, coinciding duplicates, labels on boxes,
    labels over other edges or labels, zone titles on boxes, zones holding foreign nodes or
    overlapping, and text wider than its node.
    """
    findings = []
    edges = sheet.edges
    for i, e in enumerate(edges):
        for f in edges[i + 1 :]:
            if e["pts"] == f["pts"]:
                findings.append(
                    f"EDGES COINCIDE: {e['a']}>{e['b']} #{e['index']} and #{f['index']}"
                )
                continue
            if {e["a"], e["b"]} & {f["a"], f["b"]}:
                continue  # trunks shared through a common endpoint are intended
            for s in _segments(e):
                for t in _segments(f):
                    if _collinear(s, t):
                        axis = f"y={s[0][1]:.0f}" if _horizontal(s) else f"x={s[0][0]:.0f}"
                        findings.append(
                            f"EDGES SHARE A RUN: {e['a']}>{e['b']} and {f['a']}>{f['b']} at {axis}"
                        )
    labels = [e for e in edges if e["label_box"]]
    for e in labels:
        own = _segments(e)
        for f in edges:
            if f is e:
                continue
            # A trunk segment lying on the labelled edge's own path is the same line.
            foreign = [t for t in _segments(f) if not any(_collinear(t, o) for o in own)]
            if any(_box_hits_segment(e["label_box"], t) for t in foreign):
                findings.append(
                    f"LABEL OVER EDGE: {e['a']}>{e['b']} label covers {f['a']}>{f['b']}"
                )
    for i, e in enumerate(labels):
        for f in labels[i + 1 :]:
            if _boxes_overlap(e["label_box"], f["label_box"]):
                findings.append(f"LABELS OVERLAP: {e['a']}>{e['b']} and {f['a']}>{f['b']}")
    for z in sheet.zones:
        for t in Sheet.title_boxes(z):
            for n in sheet.nodes.values():
                if _boxes_overlap(t, n):
                    findings.append(f"ZONE TITLE ON NODE: {z['id']} title covers {n['id']}")
            for e in labels:
                if _boxes_overlap(t, e["label_box"]):
                    findings.append(
                        f"ZONE TITLE ON LABEL: {z['id']} title covers {e['a']}>{e['b']}"
                    )
    for ed in edges:
        for (ax, ay), (bx, by) in _segments(ed):
            steps = max(2, int((abs(bx - ax) + abs(by - ay)) / 3))
            for n in sheet.nodes.values():
                if n["id"] in (ed["a"], ed["b"]):
                    continue
                if any(
                    _inside(ax + (bx - ax) * t / steps, ay + (by - ay) * t / steps, n, 1)
                    for t in range(steps + 1)
                ):
                    findings.append(f"EDGE THROUGH NODE: {ed['a']}>{ed['b']} crosses {n['id']}")
                    break
        lb = ed["label_box"]
        if lb:
            for n in sheet.nodes.values():
                if _boxes_overlap(lb, n):
                    findings.append(f"LABEL ON NODE: {ed['a']}>{ed['b']} label overlaps {n['id']}")
    for z in sheet.zones:
        for n in sheet.nodes.values():
            if n["id"] not in z["members"] and _inside(n["x"] + n["w"] / 2, n["y"] + n["h"] / 2, z):
                findings.append(f"ZONE HOLDS FOREIGN NODE: {z['id']} contains {n['id']}")
    for i, z in enumerate(sheet.zones):
        for o in sheet.zones[i + 1 :]:
            nested = z["members"] <= o["members"] or o["members"] <= z["members"]
            if not nested and _boxes_overlap(z, o):
                findings.append(f"ZONES OVERLAP: {z['id']} and {o['id']}")
    boxes = list(sheet.nodes.values())
    for i, n in enumerate(boxes):
        for o in boxes[i + 1 :]:
            padded = {"x": o["x"] - 12, "y": o["y"] - 12, "w": o["w"] + 24, "h": o["h"] + 24}
            if _boxes_overlap(n, padded):
                findings.append(f"NODES TOO CLOSE: {n['id']} and {o['id']}")
    for n in sheet.nodes.values():
        widest = max([len(s) * NAME_PX for s in n["names"]] + [len(s) * SUB_PX for s in n["subs"]])
        if widest > n["w"] - 8:
            findings.append(f"TEXT OVERFLOWS NODE: {n['id']}")
    return findings
