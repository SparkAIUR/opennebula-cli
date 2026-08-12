# Changelog

## 7.4.0 - 2026-08-11

This release targets OpenNebula 7.4.x while retaining the shipped 7.0.x compatibility profile.

### Added

- authenticated server-version negotiation and independently shipped 7.0/7.4 command profiles
- pre-I/O PyONE/raw routing with a no-replay mutation contract
- OpenNebula 7.4 VM exec, exec retry/cancel, and VM-group membership operations
- cluster optimization-plan operations and group VLAN rules
- OneFlow scheduled-action deletion with escaped role paths
- OneForm driver, provider, and provision REST services and compatibility wrappers
- guarded previews for `oneprovider-template` and `oneprovision-template`; stock 7.4 lacks their server routes
- invocation-scoped `--context`, fail-closed `--require-context`, and `--backend`
- context mutation-deny policy, `--password-stdin`, `doctor`, and `capabilities`
- JSON Lines, compact JSON, `--value`, `--select`, `--filter`, `--sort`, and `--no-header`
- lossless `--full` and upstream-shaped `--official-schema` inspection

### Changed

- PyONE compatibility is pinned to `>=7.3.80,<7.5`.
- all raw XML-RPC calls preserve the complete `one.*` namespace and structured faults
- raw XML pool/object responses are materialized consistently; raw output retains literal server text
- normalized state models retain both labels and numeric IDs; unknown IDs remain visible
- OneFlow service and role views expose normalized states, numeric IDs, node membership, and the complete official document
- OneForm models extract provider/provision identity from official nested documents and preserve provision state labels plus IDs
- datastore models retain total, free, and used capacity plus permissions and membership fields
- `host flush` uses the official disable-and-reschedule composite instead of nonexistent `one.host.flush`
- machine renderers bypass terminal wrapping and state/context commands honor machine output modes
- batch mutations report partial failures with non-zero exits

### Validation

- OpenNebula 7.4.0 DR: authenticated read-only list/show/full checks passed through PyONE 7.3.80 and raw XML-RPC; OneFlow list plus service/role state pairs passed
- OpenNebula 7.0.2 local protocol contract: PyONE and raw compatibility profiles passed
- generated bindings from the OpenNebula 7.4 source schema passed the focused transport/service matrix
- OneForm routes, redirect rejection, credential scoping, and preview isolation passed against a local REST fixture

No production mutation was performed. OneForm was not configured in DR, and new 7.4 mutations were validated through exact-signature, policy, partial-failure, and no-replay contract tests rather than against DR.

## 7.0.2 development baseline (unpublished)

- Added workflow template and VM initialization automation.
- Added local state locks and stored context management.
- Extended typed recovery and operational inspection surfaces.
