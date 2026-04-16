# Workflow Template Examples

This folder contains runnable examples for the new workflow templating feature.

For schema details, troubleshooting, and operational guidance, see:

- `docs/workflows-vm-templates.mdx`

The examples collectively cover:

- `one workflow template init`
- `one workflow template render` (stdout + `--output-file`)
- `one workflow template import`
- `one workflow template apply`
- `one workflow vm init`
- `one workflow vm apply`
- `cloud_init.source`
- `cloud_init.inline`
- no `cloud_init` block
- reading external files from Jinja (`read_file`, `read_file_b64`)
- fetching remote text at render-time (`fetch_url`)
- vars from YAML and JSON
- repeatable CLI overrides via `--var key=value`
- variable precedence: `defaults < --vars-file < --var`

## 0) Initialize a starter scaffold

```bash
# Create starter files in a new directory.
one workflow template init ./my-openclaw-workflow

# Overwrite starter files if they already exist.
one workflow template init ./my-openclaw-workflow --force
```

## 1) Source-Based Cloud-Init (`01-source-cloud-init`)

Use when both VM template and cloud-init live in separate files.

This example also demonstrates loading `write_files[].content` from an external file:

- `read_file("files/openclaw.env")`
- `read_file_b64("files/openclaw-bootstrap.sh")` for `encoding: b64`
- `fetch_url("https://...", method="GET", headers={...}, params={...}, timeout=10)`

If URL fetch fails (unreachable host, non-2xx response, decode failure), render/import/apply exits
with a clear `ApiError` message.

```bash
# Render to stdout.
one workflow template render \
  docs/examples/01-source-cloud-init/workflow.yaml \
  --vars-file vars.yaml

# Render to a .one file.
one workflow template render \
  docs/examples/01-source-cloud-init/workflow.yaml \
  --vars-file vars.yaml \
  --output-file /tmp/openclaw-source.one

# Import to OpenNebula (template_name must resolve to a non-empty value).
one workflow template import \
  docs/examples/01-source-cloud-init/workflow.yaml \
  --vars-file vars.yaml

# Override values from CLI (highest precedence).
one workflow template import \
  docs/examples/01-source-cloud-init/workflow.yaml \
  --vars-file vars.yaml \
  --var template_name=openclaw-user-template-b \
  --var cpu=8
```

## 2) Inline Cloud-Init (`02-inline-cloud-init`)

Use when you prefer to keep cloud-init inside `workflow.yaml`.

```bash
one workflow template render \
  docs/examples/02-inline-cloud-init/workflow.yaml \
  --vars-file vars.yaml

one workflow template apply \
  docs/examples/02-inline-cloud-init/workflow.yaml \
  --vars-file vars.yaml \
  --output-file /tmp/openclaw-inline.one
```

## 3) No Cloud-Init (`03-no-cloud-init`)

Use for templates that do not need first-boot bootstrap user data.

```bash
one workflow template render \
  docs/examples/03-no-cloud-init/workflow.yaml \
  --vars-file vars.yaml
```

## 4) JSON Vars File (`04-vars-json`)

`--vars-file` supports `.json` in addition to YAML.

```bash
one workflow template render \
  docs/examples/04-vars-json/workflow.yaml \
  --vars-file vars.json

one workflow template import \
  docs/examples/04-vars-json/workflow.yaml \
  --vars-file vars.json
```

Notes:

- JSON does not support native comments. This example uses a top-level `__comment` key as documentation.
- The importer checks for existing templates by `template_name` and fails fast on collisions.

## 5) Workflow VM Init (`05-vm-init`)

Use this for single or bulk VM initialization from an existing OpenNebula template:

```bash
# Bulk apply from YAML.
one workflow vm apply docs/examples/05-vm-init/bulk-init.yaml

# Bulk apply with operational overrides.
one workflow vm apply docs/examples/05-vm-init/bulk-init.yaml \
  --template-name openclaw-ubuntu-template \
  --set global.name_prefix=user-stage- \
  --set global.context.OPENCLAW_ENV=staging

# Single init from a selected VM entry.
one workflow vm init docs/examples/05-vm-init/bulk-init.yaml --vm-name alice

# Inline single init without file.
one workflow vm init \
  --name alice \
  --template-name openclaw-ubuntu-template \
  --set global.resources.ram=8Gi \
  --set global.context.OPENCLAW_USER=alice
```
