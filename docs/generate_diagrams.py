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


if __name__ == "__main__":
    main()
