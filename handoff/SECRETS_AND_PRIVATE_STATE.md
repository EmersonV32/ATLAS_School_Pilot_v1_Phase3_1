# Secrets and private state

Git is the recovery source for ATLAS code and versioned content, but it is not a
backup for credentials or visitor data.

## Never commit

- `.env` files and provider API keys;
- tokens, passwords, SSH private keys, certificates, or service credentials;
- visitor names, recordings, transcripts, photographs, analytics exports, or
  other identifiable session data;
- local SQLite databases and logs containing live sessions;
- generated embeddings, Chroma/vector stores, caches, and downloaded provider
  models;
- `.venv`, Python caches, test caches, IDE state, and OS-specific files.

## Safe to commit

- `.env.example` with names and non-secret placeholders;
- versioned source documents and content-pack JSON;
- dependency declarations and lock files;
- model-download instructions and integrity hashes when licensing permits;
- tests, mock fixtures, firmware source, service templates, and operational
  manuals that contain no credentials.

## Recovery source for excluded state

| State | Recovery method |
| --- | --- |
| API keys and service credentials | Reissue or restore from the team's protected password manager. |
| Python packages | Install from `atlas/requirements-jetson.lock.txt` and `atlas/pyproject.toml`. |
| Generated RAG indexes | Rebuild from versioned content sources. |
| Downloaded models/caches | Re-download using the documented setup scripts and verify hashes where supplied. |
| Live visitor/session data | Do not restore unless retention was explicitly approved and a protected backup exists. |
| Jetson environment file | Recreate from `atlas/.env.example`, then set permissions locally. |

Before every push, inspect staged file names and scan staged content for common
credential patterns. If a secret was ever committed, removing the file is not
enough: revoke or rotate the credential and clean the Git history deliberately.
