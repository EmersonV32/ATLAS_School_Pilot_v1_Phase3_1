# Pre-v6 portable checkpoint (rollback)

This is the exact seven-class checkpoint that occupied `../../atlas_yolo.pt`
before the user-requested local v6 integration on October 4, 2026.

`atlas_yolo.pt` SHA-256:
`5680d3a5fff21d482e579c47f0b19e030b6acbdefdfe5da188de9cc961a66bec`

This preserves the existing camera-domain weights, not a new training run.
The record does not claim fresh hardware validation of either checkpoint.

To roll back locally, copy this `atlas_yolo.pt` to `../../atlas_yolo.pt` and
this `manifest.sha256` to `../../manifest.sha256`, then verify the checksum and
class order. Stop a running device service before any on-device model swap;
physical changes still require explicit approval. Re-export TensorRT on that
device: engines and their generated provenance sidecars are not portable.
