# Existing Jetson: source-only deployment and rollback

Current procedure: October 26, 2026. This is for the EXISTING working Jetson,
not a fresh installation, camera flash, model update or package repair.
Start with [the teammate handoff](2026-10-26_TEAMMATE_HANDOFF.md) and both
`AGENTS.md` files. No deployment is authorized just by reading this document.

## Approval and immutable input

1. Obtain the on-site human's explicit approval for the exact source change and
   one service interruption. Confirm no filming/visitor session. Coordinate an
   exclusive device window with other active chats/operators.
2. Inspect `git status --short --branch`, recent commits and the intended diff.
   Preserve unrelated edits. Use the current continuation branch or a reviewed
   `codex/` descendant, NOT stale `main` or an old feature/archive copy.
3. Run the [validation checklist](VALIDATION_CHECKLIST.md). Commit the reviewed
   source before building. Record/push the exact SHA on the intended feature
   branch; a push does not itself deploy or authorize a `main` merge.
4. Recheck the current Jetson IP from the local console. Keep a local operator
   available, existing working credentials and a recoverable network path.

Use **`atlas/scripts/deploy/source_release.py`**. Routine updates must NOT use
the older broad `DEPLOY_ATLAS.ps1`, `bootstrap_jetson.sh`, package installs,
model-export/firmware scripts or a service-unit replacement.

The source tool's maintained CLI is `build`, `verify`, `preflight`, `apply`.
There is **no `rollback` subcommand**. Read the current script before composing
commands; do not invent options. It owns a deployment lock, refuses unsafe
paths, stages public fixtures for tests, validates using the existing venv,
then backs up/replaces only its managed paths under a stopped user service.
It automatically attempts restoration if apply fails.

## Build and verify — LOCAL laptop, from `atlas/`

Use an approved existing Python environment. The examples show `python`; on
the original Windows workspace this was `.\.venv\Scripts\python.exe`.
Do not install/upgrade anything on the live Jetson to run these steps.

Choose a NEW archive path in an existing output directory, outside Git. Replace
the public placeholders below with real paths and the checksum returned by
`build`. They are not credentials. The tool refuses an existing output file.

```bash
python scripts/deploy/source_release.py build --source-root . --output /YOUR/NEW/ATLAS-source.zip
python scripts/deploy/source_release.py verify --archive /YOUR/NEW/ATLAS-source.zip --sha256 SHA256_FROM_BUILD
```

On Windows, use a valid absolute Windows output path instead of `/YOUR/NEW/`.
Record the `SOURCE_RELEASE.json` revision, returned file count and SHA-256.
The archive includes tracked allowlisted `src/atlas`, tests and selected
scripts/metadata, plus eight validation-only public fixtures. It does not
install config, private `.env`, live data, models, venvs or service units.
New scripts outside its allowlist are NOT deployed merely because they exist;
review the manifest instead of assuming a whole-repository copy.

## Transfer — LOCAL laptop

Use SSH/SCP as `super-alex` with the current IP, strict known-host checking and
the human-approved authentication method. An `-i` path is only an option to
SSH; never open or print the private-key file. Do not bypass a changed-host-key
warning; verify the device identity with the human first.

Create a unique NEW remote staging directory with permissions 0700, for example
`/tmp/atlas-source-REVIEWED_SHA-UNIQUE`. Transfer the verified zip and the exact
reviewed `scripts/deploy/source_release.py` into it. Create a dedicated backup
parent under `/home/super-alex/atlas/backups/` on the same filesystem as the app.
Do not overwrite a prior stage, result file, backup or existing source by SCP.

Then use the existing interpreter ON THE JETSON to verify the transferred zip:

```bash
/home/super-alex/atlas/venvs/atlas-school-pilot/bin/python /tmp/YOUR_UNIQUE_STAGE/source_release.py verify --archive /tmp/YOUR_UNIQUE_STAGE/ATLAS-source.zip --sha256 SHA256_FROM_BUILD
```

The stage/archive filename and expected hash must match the actual transfer,
not the example. Compare the transport hash before any apply.

## Read-only baseline — JETSON, before applying

```bash
hostname -I
systemctl --user show atlas.service -p ActiveState -p SubState -p NRestarts -p ExecMainStatus
curl --fail --max-time 5 http://127.0.0.1:8765/health
cat /proc/sys/kernel/random/boot_id
```

Record public/sanitized service state, boot ID, intended source hashes and any
approved non-secret preservation hashes. Credential preservation may use stat
metadata ONLY, never its contents or a credential-file hash. Do not read `.env`,
visitor databases/logs/media, raw status payloads containing visitor state, or
service journal text. Do not run another camera capture or hardware loop.

Confirm the existing installation/interpreter exactly:

```text
root:   /home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated
python: /home/super-alex/atlas/venvs/atlas-school-pilot/bin/python
unit:   atlas.service, USER service under super-alex
```

If these differ, stop and reconcile them; do not rename paths, install another
service or silently redirect the release. Keep pan disabled and outputs inactive.
An optional `preflight` command accepts the same archive/hash/root/python/
backup-dir arguments and does not stop the service. `apply` already repeats
that validation, so do not waste a filming window running both without reason.

## Apply ONCE — JETSON Bash, after approval

The following is a template, not a ready-to-run command. Fill the unique stage,
zip, approved backup parent and expected hash from the verified artifact first.
Use Bash on the Jetson, NOT Windows PowerShell. All paths here are public;
no password belongs in variables or command arguments.

```bash
atlas_stage=/tmp/YOUR_UNIQUE_STAGE
atlas_archive="$atlas_stage/ATLAS-source.zip"
atlas_sha=SHA256_FROM_BUILD
atlas_python=/home/super-alex/atlas/venvs/atlas-school-pilot/bin/python
atlas_root=/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated
atlas_backups=/home/super-alex/atlas/backups/YOUR_APPROVED_BACKUP_PARENT
(
  set -eu
  umask 077
  test -d "$atlas_stage"
  test -d "$atlas_backups"
  test ! -e "$atlas_stage/apply-result.txt"
  test ! -L "$atlas_stage/apply-result.txt"
  nohup "$atlas_python" "$atlas_stage/source_release.py" apply \
    --archive "$atlas_archive" --sha256 "$atlas_sha" \
    --root "$atlas_root" --python "$atlas_python" \
    --backup-dir "$atlas_backups" --approve-stop-and-replace \
    > "$atlas_stage/apply-result.txt" 2>&1 < /dev/null &
  printf 'apply_pid=%s\n' "$!"
)
```

Do not add `--start-if-stopped` unless starting a previously stopped service is
also explicitly approved. Native staged validation can take minutes and must
pass before the source replacement. `nohup` keeps the ONE transaction running
across an SSH drop; it is not permission for unattended hardware testing.

When sending Bash through Windows SSH stdin, use the proven heredoc approach
and put a final COMMENT line after real commands so a trailing CR cannot corrupt
the final command. Do not construct commands containing secret values.

## Poll the existing transaction, never redispatch on timeout

```bash
cat "$atlas_stage/apply-result.txt"
systemctl --user show atlas.service -p ActiveState -p SubState -p NRestarts -p ExecMainStatus
```

This result file is the deployment tool's sanitized result, not an application
visitor log. An empty result while its PID is alive can mean validation is
still running. A brief SSH timeout occurred during previous successful releases:
retry bounded READ-ONLY access to the known host and inspect the same PID/result/
deployment lock. Never run a second apply, delete the lock, kill arbitrary
processes, reboot, restart networking or assume a timeout means failure.
If the device remains unreachable, use the on-site operator/local console.

## Acceptance and evidence

- Confirm successful result JSON, retained backup path and expected start state.
- Verify the installed managed file hashes against the approved manifest;
  exclude `validation/` fixtures, which are staging-only and must not overwrite
  the museum content. Archive file count differs from installed managed count.
- Check the same boot ID (a service restart is not a reboot), active/running
  user service, zero unexpected restarts and public health/UI.
- Confirm actual protected admin routes still reject unauthenticated access;
  never treat a made-up route's 404 as an authentication test. Current examples:
  `/api/admin/audio` and `/api/admin/arducam/pan/status` should return 401 without
  the admin token. Do not put that token in shell commands or shared output.
- Confirm no unintended settings, unit, model, credential metadata, network or
  PWM changes. Do not toggle pan to prove that a source release worked.
- Run focused new-feature tests with mocked providers and the dotenv guard on
  installed source when appropriate. The built-in smoke list is not every test
  in the repository; inspect `SMOKE_TESTS` before claiming a specific check ran.
- Refresh the actual browser and perform supervised demo acceptance: headset,
  intended language, one complete greeting/answer/follow-up, cancellation,
  no-camera operation and privacy. HTTP 200 is not audible/cloud acceptance.
- Record source SHA, archive SHA, file counts, tests, service result, backup and
  pending acceptance. Release the device window to peers and the human.

## Rollback and emergency recovery

The tool automatically attempts a stopped-service source restore on an apply
failure. Preserve the reported backup. If it says **ROLLBACK INCOMPLETE**, stop
new changes, keep hardware safe and obtain operator direction. Do not delete
the backup/stage, live-copy a few files, clear locks blindly or reinstall.

For a successful installation with a later behavior regression, the preferred
rollback is another explicitly approved source-only transaction built from the
previous verified COMMITTED revision in a separate clean checkout. Validate it,
get a new interruption window, and apply it through the same tool; do not reset
the shared working tree or run `cp` over a live service. Coordinate settings
compatibility before selecting an older revision. This is not firmware/model
rollback and does not restore excluded private/generated state.

Last retained source backups (verify existence; do not delete them):

| Release | Retained backup on the Jetson |
| --- | --- |
| Pronunciation, October 25 | `/home/super-alex/atlas/backups/pronunciation-20261025/atlas-source-20261025-205822-1a3b346a` |
| Navigation, October 25 | `/home/super-alex/atlas/backups/navigation-20261025/atlas-source-20261025-204741-9c167e2e` |
| Conversation, October 25 | `/home/super-alex/atlas/backups/conversation-20261025/atlas-source-20261025-200535-156386fb` |

The latest verified application revision is `4b2233c`; the preceding navigation
revision is `38e2c69`; earlier conversation revision is `5d577d9`. Pick a rollback
for the reproduced regression, not simply the oldest backup. A manual offline
restore from retained directories needs a separately reviewed, target-specific
plan with the service confirmed stopped and the current source recoverable.
There is no generic `source_release.py rollback` command.

Fresh flashing/rebuilding is a LAST, separately authorized recovery project.
Use [the rebuild guide](jetson/REBUILD_FROM_FRESH_FLASH.md) only after reading
the setup history, confirming hardware/image compatibility and protecting
private/device-generated assets. Never use a generic `apt upgrade`, package
unholds, driver/JetPack reinstall or firmware flash as a quick dashboard repair.
