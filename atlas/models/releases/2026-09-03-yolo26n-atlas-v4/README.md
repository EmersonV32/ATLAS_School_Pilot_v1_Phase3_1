# YOLO26 Nano ATLAS v4 release evidence

## Decision

This checkpoint is the deployment candidate for ATLAS because it covers all
seven content-pack artworks, is substantially smaller than the previous
checkpoint, and has strong held-out test results. It must still pass a physical
camera rehearsal and Jetson PyTorch-versus-TensorRT benchmark before the release
is frozen for competition.

## Provenance

- Source archive: `alex_training.zip`
- Source archive SHA-256: `8adc8220308abeab8572f6e7383052b28d5d034e4cf56654d864db931c51cbda`
- Checkpoint SHA-256: `6b86324bd641bfa629690d35c2c10f0dc7f4caed800db47d922ec3991543618a`
- Architecture: YOLO26 Nano, initialized from `yolo26n.pt`
- Team-owned inputs: dataset, seven-class contract, training script, settings,
  acceptance checks, and integration
- External contribution: execution of the team-authored training workflow on a
  CUDA-capable computer

## Verified results

- Training stopped after 76 recorded epochs; the best validation
  `mAP50-95` was `0.88334` at epoch 56.
- The trainer reported held-out test `mAP50 = 0.9618` and
  `mAP50-95 = 0.8486`.
- The returned held-out precision-recall plot independently rounds the overall
  test `mAP50` to `0.962`.
- Test AP50 by class: pearl earring `0.966`, great wave `0.995`, liberty
  `0.982`, Mona Lisa `0.872`, Tutankhamun mask `0.986`, Starry Night `0.967`,
  and Sunflowers `0.965`.
- Dataset audit: 866 train, 152 validation, and 152 test images; no exact file
  duplicates or repeated Roboflow source names were found across splits.
- Box counts by class are recorded in the same numeric order as the class list:
  train `200,197,225,236,218,219,213`; validation
  `34,33,53,37,37,36,52`; test `35,35,42,45,31,36,40`.

## Class order

1. `girl_with_a_pearl_earring`
2. `great_wave_off_kanagawa`
3. `liberty_leading_the_people`
4. `mona_lisa`
5. `tutankhamun_mask`
6. `starry_night`
7. `sunflowers`

## Included evidence

- `args.yaml`: exact Ultralytics training settings
- `results.csv`: epoch-by-epoch training and validation metrics
- `training_results.png`: training curves
- `test_precision_recall.png`: held-out per-class AP50 evidence
- `test_confusion_matrix_normalized.png`: held-out class and background errors

## Remaining gate

Mona Lisa is the weakest class on the held-out test set and should receive the
largest share of physical-camera testing. Record low light, glare, oblique angle,
distance, partial-frame, and non-artwork false-positive trials before freezing
the competition release.
