# MOAW workshop maintenance and publication

The root [workshop.md](../workshop.md) follows the actual
[MOAW contributing format](https://github.com/microsoft/moaw/blob/main/CONTRIBUTING.md):
one Markdown file, YAML front matter, page separators with surrounding blank lines,
and assets under [assets/](../assets/). Four identity tracks are selectable, not sequential.
No separate `index.yml` is required by that guidance.

## Preview

The workshop now includes six foldable **real logged exchanges** for the optional
upstream APIM route. Captures are historical, nonsensitive replay data; SDK baggage,
opaque consent URLs/session state and credentials must never be published.
It also includes six hosted **service response snapshots** (not runtime console
logs), the actual A-custom validated MCP console event, and a six-path evidence
matrix. Missing console logs and unobserved Search internals are explicit.
Before publishing updated excerpts, validate them against local ignored evidence.
Those exports are not available from a fresh clone; generate them with the
optional replay in an existing configured ABC lab, or retain the historical
embedded excerpts without claiming a new runtime check:

```powershell
python .\compile_observability_evidence.py
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
Source support alone does not verify browser rendering. On November 1, 2026,
the latest local workshop was previewed with the real MOAW Angular renderer at
upstream commit `99e0e09fd5f5f6c2324aa679967d10910014640c`.
The browser-fetched Markdown SHA-256 matched the local file exactly:
`af78d4375ac8473cc8279971ed43c0c07f5d20905b537726e8d892fcd1427fa3`.
All ten pages rendered, all five SVGs loaded (architecture plus four tracks),
and all 17 details blocks opened and closed with their code visible when open.
There were 64 rendered fenced code blocks, no duplicate heading IDs or raw
fences, and no hidden sidebar heading targets. C deployment headings use level
three so closed details do not create inaccessible level-two menu entries.
The public source had a different hash; this was a local-source check, not a
claim that the unpublished changes rendered on public MOAW. Repeat the check
after every workshop edit; the preview helper was stopped after verification.

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
