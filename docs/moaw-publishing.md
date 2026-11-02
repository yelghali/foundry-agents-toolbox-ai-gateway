# MOAW workshop maintenance and publication

The root [workshop.md](../workshop.md) follows
[MOAW's contributing format](https://github.com/microsoft/moaw/blob/main/CONTRIBUTING.md):
YAML front matter, ten Markdown pages separated by blank-line-delimited `---`,
and diagrams under [assets/](../assets/). No `index.yml` is required.

## Editorial layout

- Diagram first; short bullets/tables, labelled Python/PowerShell/JSON/text blocks.
- A/B retain **Azure Search MCP** and **Custom FastMCP** as visible level-two
  navigation headings; substeps use level three.
- Deployment, full selected raw exchange and identity metadata are closed native
  `<details>` / `<summary>` blocks, with blank lines around enclosed Markdown.
- Exact prompts, generated arguments, selected results/errors, six three-hop identity
  tables and 18 evidence stages remain on their owning track pages.
- One evidence legend distinguishes decoded caller, APIM validation, downstream
  validation and configuration; no repeated security narrative.
- Actual model Markdown belongs in the retained hosted response, not a visible
  fence-within-fence rendering. Use `block()` when embedding arbitrary captures.

MOAW's [menu builder](https://github.com/microsoft/moaw/blob/main/packages/website/src/app/workshop/workshop.ts)
uses headings through `baseLevel + navigation_levels - 1`; this workshop has
`navigation_levels: 2`. Do not put navigation headings inside closed folds.
The [marked renderer](https://github.com/microsoft/moaw/blob/main/packages/website/src/app/shared/markdown.ts)
preserves raw HTML; [bootstrap](https://github.com/microsoft/moaw/blob/main/packages/website/src/main.ts)
uses `sanitize: SecurityContext.NONE`. These source facts do not prove browser rendering.

## Evidence maintenance

Five selected November 1, 2026 invocations began at 12:27 UTC. C custom's selected
**post-consent upstream** invocation is 13:09:39–13:09:57 UTC:
A native/custom PASS; both B paths context-blocked; C native `AADSTS500016`;
C custom PASS with validated delegated claims. Historical direct/consent runs stay separate.

The workshop embeds each selected sanitized APIM request/response and hosted snapshot.
Repeated all-exchange arrays, full hosted responses/model text and console logs are
linked to **local ignored evidence**, not claimed available from a fresh public clone.
Fragments are JSON Pointers (`#/captures/5/hostedRuntimeLogQuery`), not HTML anchors.
The validator resolves the actual JSON value and owning scenario and checks equality;
a link label or filename alone cannot satisfy evidence validation.

After explicitly authorized collection in an existing ABC lab:

```powershell
python .\compile_observability_evidence.py
python .\update_observability_workshop.py
python .\validate_observability_docs.py
```

These commands refresh/check persisted evidence; do not silently replay Azure or
upgrade configuration into observation. Publication from a fresh clone requires
the retained embedded excerpts; linked local exports need a separately approved
sharing/retention decision. Never publish bearer tokens, keys, consent URLs or session baggage.

## Exact-source preview

Use the official MOAW Angular runtime, not a generic Markdown conversion.
The editorial review serves only local workshop/assets/approved sanitized evidence;
public renderer assets are fetched read-only, with analytics disabled. No workshop
source is uploaded. Start an **owned attached** preview, verify readiness, then stop it.

Alternatively use a separate MOAW checkout:

```powershell
git clone https://github.com/microsoft/moaw.git
New-Item -ItemType Directory .\moaw\workshops\foundry-identity
Copy-Item .\foundry-agents-toolbox-ai-gateway\workshop.md .\moaw\workshops\foundry-identity\workshop.md
Copy-Item .\foundry-agents-toolbox-ai-gateway\assets .\moaw\workshops\foundry-identity\assets -Recurse
Set-Location .\moaw
npm install --workspace=website --include-workspace-root
npm run start --workspace=website -- --host 127.0.0.1 --port 4200
```

- Open `http://localhost:4200/workshop/?src=foundry-identity/`, steps **0–9**.
  Old `step=12` bookmarks are invalid; MOAW does not clamp them.
- Compare browser-fetched Markdown SHA-256/bytes with the final local file.
- Check ten pages, diagrams, real tables, highlighted code/JSON, all folds closed
  initially and rendering when opened, sidebar target visibility and links.
- No raw fences, duplicate heading IDs or broken images; Cleanup last, no Next.
- Parse Python AST, JSON, PowerShell and YAML; resolve repository links/SVGs.
- Save current measurements/render/test evidence in
  `evidence\workshop-editorial-validation.json`; old render reviews are historical.

## Catalog submission (manual)

Public preview after an authorized commit/push:

https://aka.ms/ws?src=gh:yelghali/foundry-agents-toolbox-ai-gateway/main/

`published: true` means eligible, not submitted or pushed. Confirm public links and
author/contact metadata; fork `microsoft/moaw`, add an entry to
`packages/database/external.yml`, then submit a PR under its Code of Conduct:

```yaml
- title: Choose your Foundry agent identity with Toolbox and AI Gateway
  description: Choose project, agent, managed user or custom OAuth authorization with real evidence.
  url: https://aka.ms/ws?src=gh:yelghali/foundry-agents-toolbox-ai-gateway/main/
  language: en
  last_updated: 2026-11-01
  type: workshop
  level: advanced
  github_url: https://github.com/yelghali/foundry-agents-toolbox-ai-gateway
  authors:
    - Yael El Ghali
  contacts:
    - https://github.com/yelghali
  duration_minutes: 150
  audience: developers, solution architects
  tags: azure, foundry, agents, identity, mcp, toolbox, api-management, python
```

Editorial review does not deploy Azure, create a catalog PR, commit or push.
