# Adding or retraining artworks

This is the release gate for the ATLAS Roboflow project:
<https://app.roboflow.com/alexs-workspace-aqber/futureinnovators/>.

## Contract

Every detector class must normalize to an `artwork_id` in the active content
pack. Every content entry must have valid sources and retrieval chunks. ATLAS
must not deploy a new `.pt` or `.engine` file until this check passes.

## Workflow

1. In Roboflow, keep one class per artwork and use stable snake-case names.
2. Split by source image before augmentation so near-duplicate crops cannot
   leak between train and validation sets.
3. Include difficult negatives: frames, labels, reflections, screens, partial
   works, crowds, oblique angles, and similar-looking paintings.
4. Export the dataset/model and retain its `data.yaml` class list.
5. Add matching artwork JSON and cited chunks to the active content pack.
6. Run the contract check:

```bash
cd atlas
python scripts/validate_artwork_release.py \
  --pack data/content_packs/demo_pack \
  --labels path/to/roboflow/data.yaml \
  --require-all-content-detectable
```

7. Evaluate on a held-out physical-camera set, not Roboflow previews alone.
8. Export TensorRT only after the PyTorch model passes the same test set.
9. Run `python scripts/benchmark_yolo_backends.py` on the Jetson.
10. Keep the previous model and the Git snapshot tag until the new release has
    passed a complete judge-demo rehearsal.

## Acceptance gate

- The validator exits with code `0` and reports no warnings in strict mode.
- No class maps to the wrong artwork in the physical-camera holdout.
- Unknown and ambiguous views stay below the interaction threshold.
- Manual capture still works when automatic recognition is uncertain.
- Camera reconnect, sustained hold, and demo-mode tests pass on the Jetson.

`config/artwork_labels.yaml` records the class contract for the currently
deployed content. Update it in the same commit as a released detector.
