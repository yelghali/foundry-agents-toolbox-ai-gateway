# MOAW workshop maintenance and publication

The root [workshop.md](../workshop.md) follows the actual
[MOAW contributing format](https://github.com/microsoft/moaw/blob/main/CONTRIBUTING.md):
one Markdown file, YAML front matter, page separators with surrounding blank lines,
and assets under [assets/](../assets/). Four identity tracks are selectable, not sequential.
No separate `index.yml` is required by that guidance.

## Preview

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
npm install
npm start
```

Open `http://localhost:4200/workshop/?src=foundry-identity/`. These npm commands
belong to **MOAW**, not this Python infrastructure repository. Stop the preview
server afterward. Verify all pages, the architecture image, navigation and links.
The workshop uses absolute GitHub implementation links because its sample code lives
outside the MOAW asset directory. Implementation links target `main`; maintain them
alongside code changes.

## Foldable deployment blocks

Use native `<details>` / `<summary>` with blank lines around the enclosed Markdown.
Each track keeps its diagram, integration code and proof exercise visible; only
prerequisites and deployment commands are collapsed.
MOAW's [marked options](https://github.com/microsoft/moaw/blob/main/packages/website/src/app/shared/markdown.ts)
retain raw HTML, and its [bootstrap configuration](https://github.com/microsoft/moaw/blob/main/packages/website/src/main.ts)
sets `sanitize: SecurityContext.NONE`, preserving these browser-native elements.
This verifies source support, not a running frontend: browser foldability and
all-page rendering remain unverified until the preview procedure above is run.

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
