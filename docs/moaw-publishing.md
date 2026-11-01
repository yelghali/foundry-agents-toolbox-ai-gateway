# MOAW workshop maintenance and publication

The root [workshop.md](../workshop.md) follows the actual
[MOAW contributing format](https://github.com/microsoft/moaw/blob/main/CONTRIBUTING.md):
one Markdown file, YAML front matter, page separators with surrounding blank lines,
and assets under [assets/](../assets/). Four identity tracks are selectable, not sequential.
No separate `index.yml` is required by that guidance.

## Preview

The workshop now includes six foldable **real logged exchanges** for the optional
upstream APIM route, freshly replayed on November 1, 2026 using pinned hosted
versions. Three numbered stages per scenario show the exact prompt/hosted
response, generated tool arguments or blocked discovery, and actual log evidence.
The latest selected captures began at 12:27 UTC. Each scenario also separates
caller decoded-only, APIM-validated and (where observed) MCP-validated JWT claims
in a three-hop table. The platform principal is the calling agent instance even
in A; A custom's project MI is downstream, not the inbound bearer.
Full captures remain secondary foldables. Captures use nonsensitive replay data; SDK baggage,
opaque consent URLs/session state and credentials must never be published.
It also includes six hosted **service response snapshots** (not runtime console
logs), the actual A-custom validated MCP console event, and a six-path evidence
matrix. Missing console logs and unobserved Search internals are explicit.
Before publishing updated excerpts, validate them against local ignored evidence.
Those exports are not available from a fresh clone; generate them with the
optional replay in an existing configured ABC lab, or retain the historical
embedded excerpts without claiming a new runtime check:

```powershell
python .\collect_hosted_runtime_logs.py --config $configPath
python .\compile_observability_evidence.py
python .\update_observability_workshop.py
python .\validate_observability_docs.py
```

Keep blocked results visibly blocked. An HTTP 200 wrapper with JSON-RPC error,
configured target URL, or an old MCP console event is not a successful current run.
Internal Search queries were not captured and must not be fabricated.

Once this change is committed and pushed to the public `main` branch, open:

https://aka.ms/ws?src=gh:yelghali/foundry-agents-toolbox-ai-gateway/main/

Before pushing, preview with a separate clone of the public MOAW repository:

```powershell
# From a workspace containing both repositories as sibling folders.
git clone https://github.com/microsoft/moaw.git
New-Item -ItemType Directory .\moaw\workshops\foundry-identity
Copy-Item .\foundry-agents-toolbox-ai-gateway\workshop.md .\moaw\workshops\foundry-identity\workshop.md
```

Then copy the workshop assets:

```powershell
Copy-Item .\foundry-agents-toolbox-ai-gateway\assets .\moaw\workshops\foundry-identity\assets -Recurse
Set-Location .\moaw
npm install --workspace=website --include-workspace-root
npm run start --workspace=website -- --host 127.0.0.1 --port 4200
```

Open `http://localhost:4200/workshop/?src=foundry-identity/`. These npm commands
belong to **MOAW**, not this Python infrastructure repository. Stop the preview
server afterward. Verify all pages, the architecture image, navigation and links.
Use `step=0` through `step=9` for the ten pages. Old bookmarks such as `step=12`
are out of range after consolidation; remove `step` or navigate from the first
page. MOAW does not clamp an invalid step to the last page.
The workshop uses absolute GitHub implementation links because its sample code lives
outside the MOAW asset directory. Implementation links target `main`; maintain them
alongside code changes.

## Target navigation in A and B

Keep **Azure Search MCP** and **Custom FastMCP** as level-two headings outside
foldable blocks. Use level-three headings for deployment, agent, connection and
server steps; do not add generic level-two steps between the target choices.
MOAW's [menu builder](https://github.com/microsoft/moaw/blob/main/packages/website/src/app/workshop/workshop.ts)
includes headings up to `baseLevel + navigation_levels - 1`: with this workshop's
`navigation_levels: 2` and level-one page titles, only level-two headings become
submenu entries. Each page resets its heading slugs, so the same target names
can safely appear in both independent tracks. Confirm both choices in the
sidebar during preview; this source check is not browser-rendering evidence.

## Foldable deployment blocks

Use native `<details>` / `<summary>` with blank lines around the enclosed Markdown.
Each track keeps its diagram, integration code and proof exercise visible; only
prerequisites and deployment commands are collapsed.
MOAW's [marked options](https://github.com/microsoft/moaw/blob/main/packages/website/src/app/shared/markdown.ts)
retain raw HTML, and its [bootstrap configuration](https://github.com/microsoft/moaw/blob/main/packages/website/src/main.ts)
sets `sanitize: SecurityContext.NONE`, preserving these browser-native elements.
Source support alone does not verify browser rendering. The fresh November 1,
2026 replay edition was previewed with the official MOAW Angular static runtime
(displayed build `sha.99e0e09`) served locally on an attached, workshop-only server.
Local npm restoration was unavailable; public renderer assets were fetched
read-only into memory, while the workshop and SVGs remained local. No workshop
source was uploaded or published. The latest identity-hop edition reused the
existing attached preview and public renderer checkout without another install.
Its browser-fetched Markdown SHA-256 matched the local file exactly:
`7fffdc1747243a7597c52ce2ac462ac7ea67c804c6235878c80f939a2384fc29`
(321010 bytes).
All ten pages rendered, all five SVGs loaded, and all 16 details blocks opened
and closed with their code visible when open. The 18 scenario stages were visible
outside details; there were no duplicate heading IDs, raw fences, broken images
or hidden sidebar targets. Cleanup was last, with no Next button.
Six identity lessons and all 18 numbered stages rendered outside details.
Embedded model Markdown uses longer outer fences so an actual fenced answer
cannot hide the next stage. Python AST, JSON and PowerShell parsing passed for
16, 58 and 19 snippets respectively. The complete current offline suite ran
82 tests: 77 passed, 5 skipped (superseding the earlier 76-test review).
Current browser results are saved locally in
`evidence\workshop-render-review-current.json`; the earlier review remains
historical. Repeat this exact-source check after edits. This check reused an
already-running attached helper; it did not start or detach a new server.

## Catalog submission (manual)

Confirm the public source URL works and author/contact metadata is correct before
requesting publication. `published: true` makes the document eligible; it does not
create a catalog entry or push your local edits.

Following the official contributing guide, fork `microsoft/moaw`, add an entry to
`packages/database/external.yml`, and submit a PR explaining the workshop's goal.
Read MOAW's Code of Conduct. A proposed entry is:

```yaml
- title: Choose your Foundry agent identity with Toolbox and AI Gateway
  description: Deploy a shared lab foundation and choose project, agent, managed user, or custom OAuth authorization with real allow/deny evidence.
  url: https://aka.ms/ws?src=gh:yelghali/foundry-agents-toolbox-ai-gateway/main/
  language: en
  last_updated: 2026-10-31
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

No catalog PR, Azure deployment, commit or push is performed as part of writing
these workshop files. A full runtime proof requires a participant's own tenant,
preview access and billable infrastructure.
