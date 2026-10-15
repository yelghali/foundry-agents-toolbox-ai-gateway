"""Generate matching SVG and editable Excalidraw architecture from a single layout."""

import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).parent


def main():
    elements = []
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1680" height="1060" viewBox="0 0 1680 1060" style="max-width:100%;height:auto" role="img" aria-labelledby="title desc">',
           '<title id="title">Foundry A/B/C identity and APIM placements</title>',
           '<desc id="desc">A uses project identity and APIM before Toolbox. B uses agent identity and APIM after Toolbox. C uses end-user identity and APIM before the agent. Each project has isolated Search and telemetry.</desc>',
           '<rect width="1680" height="1060" fill="white"/>',
           '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#495057"/></marker></defs>']

    def text(id_, x, y, value, size=18, width=1500):
        lines = value.splitlines()
        elements.append({
            "id": id_, "type": "text", "x": x, "y": y, "width": width,
            "height": size * 2.5 * len(lines), "text": value, "originalText": value,
            "fontSize": size, "fontFamily": 2, "strokeColor": "#000000",
            "textAlign": "left", "verticalAlign": "top", "lineHeight": 1.25,
            "version": 1, "versionNonce": 1, "isDeleted": False, "seed": 1,
        })
        svg.append(f'<text x="{x}" y="{y + size}" font-family="Segoe UI,Arial,sans-serif" font-size="{size}" fill="#000000">')
        for i, line in enumerate(lines):
            svg.append(f'<tspan x="{x}" dy="{0 if i == 0 else size * 1.4}">{escape(line)}</tspan>')
        svg.append("</text>")

    def box(id_, x, y, value, color, fill, width=230):
        elements.append({
            "id": id_, "type": "rectangle", "x": x, "y": y, "width": width, "height": 110,
            "strokeColor": color, "backgroundColor": fill, "fillStyle": "solid",
            "strokeWidth": 2, "roughness": 0, "roundness": {"type": 3},
            "seed": 1, "version": 1, "versionNonce": 1, "isDeleted": False,
            "boundElements": [{"id": id_ + "-text", "type": "text"}],
        })
        svg.append(f'<rect x="{x}" y="{y}" width="{width}" height="110" rx="10" fill="{fill}" stroke="{color}" stroke-width="2"/>')
        text(id_ + "-text", x + 14, y + 22, value, 17, width - 28)
        elements[-1]["containerId"] = id_
        elements[-1]["textAlign"] = "center"
        elements[-1]["verticalAlign"] = "middle"

    def arrow(id_, x, y, length):
        elements.append({
            "id": id_, "type": "arrow", "x": x, "y": y, "width": length, "height": 0,
            "points": [[0, 0], [length, 0]], "strokeColor": "#495057", "strokeWidth": 2,
            "endArrowhead": "arrow", "startArrowhead": None, "roughness": 0,
            "seed": 1, "version": 1, "versionNonce": 1, "isDeleted": False,
        })
        svg.append(f'<path d="M{x},{y} h{length}" stroke="#495057" stroke-width="2" marker-end="url(#arrow)"/>')

    text("heading", 40, 20, "One lab, three authorization identities", 30)
    text("subtitle", 40, 75, "APIM Standard v2 | separate Search services and App Insights | historical live findings", 18)
    rows = [
        ("a", 155, "A - Project identity", "#0078D4", "#CFE4FA", [
            "User", "Prompt / hosted\nagent A", "APIM\nplatform token", "Toolbox\nproject credential", "Search A\nindex-a / kb-a",
        ], "Search sees project A MI. AB -> Search B / KB B is denied."),
        ("b", 385, "B - Agent identity", "#5C2D91", "#E8DAEF", [
            "User", "Prompt / hosted\nagent B", "Toolbox\nagent credential", "APIM\nagent Search token", "Search B\nindex-b / kb-b",
        ], "APIM sees each agent's distinct oid. BC -> Search C / KB C is denied."),
        ("c", 615, "C - End-user identity", "#107C10", "#DFF6DD", [
            "User", "APIM\nuser platform token", "Prompt / hosted\nagent C", "Toolbox\nmanaged user OBO", "IQ KB C\nlocal index-c",
        ], "APIM correlates the user; no Search data grant to project C or its agents."),
    ]
    for label, y, title, color, fill, boxes, note in rows:
        text(label + "-title", 40, y - 40, title, 22)
        for i, value in enumerate(boxes):
            x = 40 + i * 325
            box(f"{label}-{i}", x, y, value, color, fill)
            if i < len(boxes) - 1:
                arrow(f"{label}-arrow-{i}", x + 240, y + 55, 70)
        text(label + "-note", 40, y + 125, note, 18)
    text("telemetry", 40, 860, "Per project: Application Insights + Log Analytics; metadata-only custom events and APIM body logging disabled.", 18)
    text("privacy", 40, 910, "B-confidential: question audit + direct model endpoint + forced store:false; answers excluded from tested telemetry.", 18)
    text("limits", 40, 960, "Limits: not one multi-index KB; no document-ACL proof; C raw Search blocked; optional OAuth needs consent.", 18)
    text("sku", 40, 1000, "This is not the dedicated AI Gateway preview tier. No claim of zero provider/internal retention.", 18)
    svg.append("</svg>")
    scene = {"type": "excalidraw", "version": 2, "source": "foundry-agents-toolbox-ai-gateway",
             "elements": elements, "appState": {"viewBackgroundColor": "#ffffff"}, "files": {}}
    (ROOT / "architecture.excalidraw").write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")
    (ROOT / "architecture.svg").write_text("\n".join(svg) + "\n", encoding="utf-8")
    generate_secure_architecture()


def generate_secure_architecture():
    elements = []
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1900" height="1320" viewBox="0 0 1900 1320" style="max-width:100%;height:auto" role="img" aria-labelledby="secure-title secure-desc">',
        '<title id="secure-title">Recommended secure Foundry agent architecture</title>',
        '<desc id="secure-desc">Recommended architecture separates user ingress, agent and user tool identities, Search and knowledge base trust boundaries, model gateways, and content-minimized telemetry.</desc>',
        '<rect width="1900" height="1320" fill="white"/>',
        '<defs><marker id="secure-arrow" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#495057"/></marker></defs>',
    ]

    def text(id_, x, y, value, size=18, width=1500, align="left"):
        lines = value.splitlines()
        element = {
            "id": id_, "type": "text", "x": x, "y": y, "width": width,
            "height": size * 2.5 * len(lines), "text": value, "originalText": value,
            "fontSize": size, "fontFamily": 2, "strokeColor": "#000000",
            "textAlign": align, "verticalAlign": "top", "lineHeight": 1.25,
            "version": 1, "versionNonce": 1, "isDeleted": False, "seed": 2,
        }
        elements.append(element)
        anchor = "middle" if align == "center" else "start"
        svg_x = x + width / 2 if align == "center" else x
        svg.append(
            f'<text x="{svg_x}" y="{y + size}" text-anchor="{anchor}" '
            f'font-family="Segoe UI,Arial,sans-serif" font-size="{size}" fill="#000000">'
        )
        for i, line in enumerate(lines):
            svg.append(
                f'<tspan x="{svg_x}" dy="{0 if i == 0 else size * 1.35}">{escape(line)}</tspan>'
            )
        svg.append("</text>")

    def box(id_, x, y, value, color, fill, width, height, size=16):
        elements.append({
            "id": id_, "type": "rectangle", "x": x, "y": y, "width": width, "height": height,
            "strokeColor": color, "backgroundColor": fill, "fillStyle": "solid",
            "strokeWidth": 2, "roughness": 0, "roundness": {"type": 3},
            "seed": 2, "version": 1, "versionNonce": 1, "isDeleted": False,
            "boundElements": [{"id": id_ + "-text", "type": "text"}],
        })
        svg.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="10" '
            f'fill="{fill}" stroke="{color}" stroke-width="2"/>'
        )
        lines = value.splitlines()
        elements.append({
            "id": id_ + "-text", "type": "text", "x": x + 12, "y": y + 12,
            "width": width - 24, "height": size * 2.5 * len(lines),
            "text": value, "originalText": value, "fontSize": size, "fontFamily": 2,
            "strokeColor": "#000000", "textAlign": "center", "verticalAlign": "middle",
            "lineHeight": 1.25, "containerId": id_, "version": 1, "versionNonce": 1,
            "isDeleted": False, "seed": 2,
        })
        center_x = x + width / 2
        first_y = y + height / 2 - ((len(lines) - 1) * size * 1.35) / 2
        svg.append(
            f'<text x="{center_x}" y="{first_y}" text-anchor="middle" '
            f'font-family="Segoe UI,Arial,sans-serif" font-size="{size}" fill="#000000">'
        )
        for i, line in enumerate(lines):
            svg.append(
                f'<tspan x="{center_x}" dy="{0 if i == 0 else size * 1.35}">{escape(line)}</tspan>'
            )
        svg.append("</text>")

    def container(id_, x, y, width, height, color, label):
        elements.append({
            "id": id_, "type": "rectangle", "x": x, "y": y, "width": width, "height": height,
            "strokeColor": color, "backgroundColor": "transparent", "fillStyle": "solid",
            "strokeWidth": 2, "roughness": 0, "roundness": {"type": 3},
            "seed": 2, "version": 1, "versionNonce": 1, "isDeleted": False,
        })
        svg.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="14" '
            f'fill="none" stroke="{color}" stroke-width="2"/>'
        )
        text(id_ + "-label", x + 20, y + 14, label, 22, width - 40)

    def arrow(id_, x1, y1, x2, y2, label=None, dashed=False):
        dash = "8 7" if dashed else None
        element = {
            "id": id_, "type": "arrow", "x": x1, "y": y1,
            "width": abs(x2 - x1), "height": abs(y2 - y1),
            "points": [[0, 0], [x2 - x1, y2 - y1]], "strokeColor": "#495057",
            "strokeWidth": 2, "endArrowhead": "arrow", "startArrowhead": None,
            "roughness": 0, "seed": 2, "version": 1, "versionNonce": 1,
            "isDeleted": False,
        }
        if dash:
            element["strokeStyle"] = "dashed"
        elements.append(element)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        svg.append(
            f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="#495057" '
            f'stroke-width="2"{dash_attr} marker-end="url(#secure-arrow)"/>'
        )
        if label:
            label_width = 210
            label_x = (x1 + x2) / 2 - label_width / 2
            label_y = (y1 + y2) / 2 - 30
            text(id_ + "-label", label_x, label_y, label, 14, label_width, "center")

    text("secure-heading", 40, 20, "Recommended secure Foundry agent architecture", 32, 1800)
    text(
        "secure-subtitle", 40, 78,
        "Identity findings are live-verified; private networking is the recommended target and was not fully exercised by this lab.",
        18, 1800,
    )
    box(
        "secure-insight", 40, 125,
        "Enforcement = identity + downstream RBAC + isolated Search / KB / gateway boundaries.\n"
        "Toolbox, APIM and telemetry improve authentication and visibility; they do not create per-index RBAC.",
        "#F7630C", "#FFF4CE", 1820, 82, 18,
    )

    container("auth-plane", 30, 235, 1120, 500, "#0078D4", "1. Tool and data authorization plane")
    box("caller", 70, 325, "User / app\nEntra ID", "#0078D4", "#CFE4FA", 180, 110)
    box(
        "ingress-apim", 300, 315,
        "APIM ingress\nvalidate JWT\nrate limit\ncorrelation ID",
        "#F7630C", "#FFF4CE", 220, 130,
    )
    box(
        "foundry-agent", 570, 315,
        "Foundry agent\nexplicit orchestration\n(no automatic A2A)",
        "#107C10", "#DFF6DD", 220, 130,
    )
    box(
        "toolbox", 840, 315,
        "Toolbox\nselect per-tool auth\nproject / agent / user",
        "#5C2D91", "#E8DAEF", 250, 130,
    )
    arrow("caller-ingress", 250, 380, 300, 380, "user JWT")
    arrow("ingress-agent", 520, 380, 570, 380, "user + correlation")
    arrow("agent-toolbox", 790, 380, 840, 380, "tool call")
    text("identity-choice", 300, 470, "Choose one connection identity per tool:", 17, 790)
    box(
        "project-identity", 300, 515,
        "Project MI\nshared project access\nVerified: IQ A",
        "#0078D4", "#CFE4FA", 230, 145,
    )
    box(
        "agent-identity", 570, 515,
        "Agent identity\nper-agent least privilege\nVerified: B / deny C",
        "#5C2D91", "#E8DAEF", 230, 145,
    )
    box(
        "user-identity", 840, 515,
        "User token / OBO\nVerified: trusted IQ\nOAuth + APIM fallback",
        "#107C10", "#DFF6DD", 250, 145,
    )
    text(
        "auth-note", 70, 680,
        "Same project != automatic agent-to-agent permission. Configure agent references and supported orchestration explicitly.",
        16, 1020,
    )

    container("data-plane", 1180, 235, 690, 500, "#D13438", "2. Enforce resource boundaries")
    box(
        "data-apim", 1220, 315,
        "APIM data gateway\nvalidate caller / OBO\nlog path + oid\nbody logging off",
        "#F7630C", "#FFF4CE", 250, 145,
    )
    box("boundary-a", 1530, 280, "Boundary A\nSearch service A + KB A", "#0078D4", "#CFE4FA", 290, 105)
    box("boundary-b", 1530, 415, "Boundary B\nSearch service B + KB B", "#5C2D91", "#E8DAEF", 290, 105)
    box("boundary-c", 1530, 550, "Boundary C\nSearch service C + KB C", "#107C10", "#DFF6DD", 290, 105)
    arrow("toolbox-data-apim", 1090, 380, 1220, 380, "agent / user token")
    arrow("data-a", 1470, 350, 1530, 332, "RBAC")
    arrow("data-b", 1470, 375, 1530, 467, "RBAC")
    arrow("data-c", 1470, 400, 1530, 602, "RBAC")
    box(
        "index-warning", 1210, 525,
        "Do not use one multi-index KB\nas the only strict authorization boundary.",
        "#D13438", "#FDE7E9", 280, 120, 16,
    )
    text(
        "network-target", 1210, 675,
        "Recommended target: Private Link / existing VNet\n"
        "and deny-by-default public access where supported.",
        15, 620,
    )

    container("model-plane", 30, 770, 1120, 420, "#107C10", "3. Model authorization plane")
    box("model-agent", 70, 875, "Prompt agent", "#107C10", "#DFF6DD", 210, 120)
    box(
        "admin-connection", 330, 855,
        "Admin-connected model\nModelGateway / ApiManagement\nexact model alias\ncredential in connection",
        "#5C2D91", "#E8DAEF", 250, 160,
    )
    box(
        "dedicated-gateway", 640, 855,
        "Dedicated AI Gateway\none per trust boundary\nruntime key scope = gateway",
        "#F7630C", "#FFF4CE", 250, 160,
    )
    box("backend-model", 950, 875, "Foundry model\nbackend", "#0078D4", "#CFE4FA", 160, 120)
    arrow("agent-connection", 280, 935, 330, 935, "model reference")
    arrow("connection-gateway", 580, 935, 640, 935, "API key")
    arrow("gateway-model", 890, 935, 950, 935, "gateway MI\nFoundry User")
    box(
        "gateway-warning", 330, 1050,
        "A runtime key reaches every published asset in one gateway.\n"
        "Use separate gateways for authorization isolation.",
        "#D13438", "#FDE7E9", 560, 92, 17,
    )

    container("observability", 1180, 770, 690, 420, "#0C8599", "4. Correlated, content-minimized observability")
    box(
        "project-ai", 1210, 855,
        "Project App Insights\nuser oid / agent id\ncorrelation ID\nno answer content",
        "#0078D4", "#CFE4FA", 190, 165,
    )
    box(
        "apim-ai", 1430, 855,
        "APIM App Insights\nroute / status / caller\nbody logging off",
        "#F7630C", "#FFF4CE", 190, 165,
    )
    box(
        "gateway-ai", 1650, 855,
        "Gateway App Insights\ntoken metrics\nkey identity\nnot user oid",
        "#107C10", "#DFF6DD", 190, 165,
    )
    arrow("project-apim-correlation", 1400, 938, 1430, 938, "correlation ID", True)
    arrow("apim-gateway-correlation", 1620, 938, 1650, 938, "correlation ID", True)
    box(
        "privacy-note", 1210, 1050,
        "Telemetry is evidence, not authorization. store:false and content filtering reduce export;\n"
        "they are not a zero-provider-retention guarantee.",
        "#495057", "#F3F2F1", 630, 92, 16,
    )

    text(
        "secure-footer", 40, 1235,
        "Live-verified: project / agent / user IQ identities, deny paths and dedicated-gateway BYOM. "
        "Recommended target: private networking and separate deployments per trust boundary.",
        16, 1800,
    )
    svg.append("</svg>")
    scene = {
        "type": "excalidraw", "version": 2, "source": "foundry-agents-toolbox-ai-gateway",
        "elements": elements, "appState": {"viewBackgroundColor": "#ffffff"}, "files": {},
    }
    (ROOT / "recommended-secure-architecture.excalidraw").write_text(
        json.dumps(scene, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "recommended-secure-architecture.svg").write_text(
        "\n".join(svg) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
