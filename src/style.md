# Shared style contract

Every diagram in `src/` uses **only** the classes and icons below. `bin/verify --lint` rejects a
`class` reference that is not defined here. Do not invent per-diagram colors — the whole atlas has
to read as one system.

## Palette

Nine planes. Fills are light and text is near-black in every class, so the same diagram is legible
in Obsidian light **and** dark themes and in the artifact's light and dark modes. Never rely on the
renderer's default node color: a default-styled node is invisible in one theme or the other.

| Class | Plane | Fill | Stroke | Text |
|---|---|---|---|---|
| `host` | the machine itself, host-network processes | `#e8eaf0` | `#4a5568` | `#1a202c` |
| `ingress` | front doors, proxies, tunnels, DNS | `#e0e7ff` | `#4f46e5` | `#1e1b4b` |
| `media` | media apps and the *arr pipeline | `#ffedd5` | `#ea580c` | `#431407` |
| `data` | storage, databases, sync, volumes | `#ccfbf1` | `#0d9488` | `#042f2e` |
| `ai` | the agent plane: bridges, MCP, bots | `#fae8ff` | `#a21caf` | `#4a044e` |
| `vpn` | VPN egress and the containers behind it | `#dbeafe` | `#2563eb` | `#172554` |
| `secure` | encrypted or egress-blocked, enforced boundary | `#fee2e2` | `#dc2626` | `#450a0a` |
| `external` | off-box: cloud, ISP, third-party services | `#f1f5f9` | `#94a3b8` | `#0f172a` |
| `warn` | degraded, stale, or known-broken **as observed** | `#fef9c3` | `#ca8a04` | `#422006` |

Paste block — copy verbatim into every `.mmd`:

```
classDef host fill:#e8eaf0,stroke:#4a5568,stroke-width:1.5px,color:#1a202c
classDef ingress fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#1e1b4b
classDef media fill:#ffedd5,stroke:#ea580c,stroke-width:1.5px,color:#431407
classDef data fill:#ccfbf1,stroke:#0d9488,stroke-width:1.5px,color:#042f2e
classDef ai fill:#fae8ff,stroke:#a21caf,stroke-width:1.5px,color:#4a044e
classDef vpn fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
classDef secure fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#450a0a
classDef external fill:#f1f5f9,stroke:#94a3b8,stroke-width:1.5px,color:#0f172a
classDef warn fill:#fef9c3,stroke:#ca8a04,stroke-width:2px,color:#422006
```

`warn` is reserved for things observed broken on the box, never for things merely disliked. A node
in `warn` must have a footnote in its sidecar saying what was observed and when.

## Icons

Emoji prefix in the node label, one per node kind. The artifact swaps these for inline SVG vendor
logos; the emoji stay in the mermaid so the workspace notes read well on their own.

| Icon | Kind | | Icon | Kind |
|---|---|---|---|---|
| 🖥️ | physical host / device | | 📦 | container |
| 🌐 | network / subnet | | ⚙️ | systemd unit |
| ⏰ | timer / schedule | | 💾 | volume / bind mount |
| 🔀 | proxy / router | | 🔒 | encrypted store |
| 🛡️ | VPN egress | | 🤖 | agent / LLM |
| 🎬 | video | | 🎵 | music |
| 📚 | books | | 📷 | photos |
| 🗃️ | database | | 🔁 | sync |
| ☁️ | cloud service | | 📡 | tunnel / overlay |
| 📱 | phone | | 💬 | messaging |
| 🔍 | indexer / search | | ⬇️ | downloader |

## Syntax subset

Only `flowchart` (`LR`/`TD`), `sequenceDiagram`, `subgraph`/`end`, `classDef`, `class`, and `%%`
comments. No `mindmap`, `C4Context`, `block-beta`, `architecture-beta`, styling directives, or
front-matter config — those vary between the Obsidian-bundled mermaid and the artifact runtime, and
a diagram that renders in one and errors in the other is worse than no diagram.

Edge labels use `-->|label|`. Dashed `-.->` means "control or metadata path"; solid means "data
path". Thick `==>` means "the primary flow this diagram is about".

## Node id convention

Node ids are the **real system identifier** wherever one exists, with `-` replaced by `_`:
container name (`gluetun_books`), unit name (`homelab_mcp_service`), network name
This keeps sidecar identifiers checkable against the declared inventory.
Ids that are concepts rather than real objects are prefixed `x_` (e.g. `x_internet`) and are
exempt from drift checking.
