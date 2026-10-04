"""Train one ATLAS v6 model and package the checkpoint and evaluation results."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / 'dataset'
RUNS = ROOT / 'runs'
RUN_NAME = 'yolo26n-atlas-v6'
ULTRALYTICS_VERSION = '8.4.163'
CLASSES = [
    'girl_with_a_pearl_earring', 'great_wave_off_kanagawa',
    'liberty_leading_the_people', 'mona_lisa', 'tutankhamun_mask',
    'starry_night', 'sunflowers',
]


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def package_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f'Path outside the extracted package: {relative}')
    return path


def preflight() -> dict[str, Any]:
    """Verify the complete training input before importing GPU libraries."""
    metadata = json.loads((DATASET / 'data.yaml').read_text(encoding='utf-8'))
    if metadata.get('names') != CLASSES or metadata.get('nc') != len(CLASSES):
        raise ValueError('Class contract changed; use the supplied dataset/data.yaml.')
    entries = json.loads((ROOT / 'dataset_manifest.json').read_text(encoding='utf-8'))
    expected = json.loads((ROOT / 'dataset_preparation.json').read_text(encoding='utf-8'))
    stats: dict[str, Any] = {}
    sources: dict[str, set[str]] = defaultdict(set)
    groups: dict[str, set[str]] = defaultdict(set)
    hashes: dict[str, set[str]] = defaultdict(set)
    seen_paths: set[str] = set()
    for split in ['train', 'valid', 'test']:
        counts: Counter[int] = Counter()
        images = negatives = boxes = 0
        for entry in entries:
            if entry['split'] != split:
                continue
            image = package_path(entry['image'])
            label = package_path(entry['label'])
            if entry['image'] in seen_paths:
                raise ValueError(f'Duplicate manifest image: {entry["image"]}')
            seen_paths.add(entry['image'])
            if image.parent != DATASET / split / 'images' or label.parent != DATASET / split / 'labels':
                raise ValueError(f'Manifest split/path mismatch: {entry["image"]}')
            if image.stem != label.stem:
                raise ValueError(f'Image/annotation names do not match: {image.name}')
            if not image.is_file() or sha256(image) != entry['image_sha256']:
                raise ValueError(f'Missing or modified image: {entry["image"]}')
            if not label.is_file() or sha256(label) != entry['label_sha256']:
                raise ValueError(f'Missing or modified annotation: {entry["label"]}')
            rows = [line.split() for line in label.read_text(encoding='utf-8').splitlines() if line.strip()]
            for row in rows:
                if len(row) != 5:
                    raise ValueError(f'Invalid box format: {label.name}')
                cls = int(row[0])
                x, y, w, h = map(float, row[1:])
                if not 0 <= cls < len(CLASSES) or not all(math.isfinite(v) for v in [x, y, w, h]):
                    raise ValueError(f'Invalid box class/coordinate: {label.name}')
                if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
                    raise ValueError(f'Box outside normalized coordinates: {label.name}')
                if min(x - w/2, y - h/2) < -0.001 or max(x + w/2, y + h/2) > 1.001:
                    raise ValueError(f'Box extends outside image: {label.name}')
                counts[cls] += 1
            images += 1
            boxes += len(rows)
            negatives += not rows
            sources[entry['source_id']].add(split)
            groups[entry['capture_group']].add(split)
            hashes[entry['image_sha256']].add(split)
        actual_images = {p.name for p in (DATASET / split / 'images').iterdir() if p.is_file()}
        actual_labels = {p.name for p in (DATASET / split / 'labels').iterdir() if p.is_file()}
        expected_images = {Path(e['image']).name for e in entries if e['split'] == split}
        expected_labels = {Path(e['label']).name for e in entries if e['split'] == split}
        if actual_images != expected_images or actual_labels != expected_labels:
            raise ValueError(f'Unexpected or missing files in {split}; extract a fresh copy.')
        stats[split] = {
            'images': images, 'boxes': boxes, 'negative_images': int(negatives),
            'class_boxes': {name: counts[i] for i, name in enumerate(CLASSES)},
        }
        if any(counts[i] == 0 for i in range(len(CLASSES))):
            raise ValueError(f'{split} lacks examples of a class.')
        for field in ['images', 'boxes', 'negative_images', 'class_boxes']:
            if stats[split][field] != expected['prepared_splits'][split][field]:
                raise ValueError(f'{split} does not match the reviewed {field}.')
    for name, mapping in [('source identifier', sources), ('capture group', groups), ('image hash', hashes)]:
        overlaps = [key for key, splits in mapping.items() if len(splits) > 1]
        if overlaps:
            raise ValueError(f'{name} occurs across splits: {overlaps[:3]}')
    return {'passed': True, 'splits': stats, 'classes': CLASSES,
            'source_archive_sha256': expected['source_archive_sha256'],
            'limitations': expected['limitations']}


def resolved_dataset() -> Path:
    metadata = json.loads((DATASET / 'data.yaml').read_text(encoding='utf-8'))
    metadata['path'] = DATASET.resolve().as_posix()
    destination = RUNS / 'data_resolved.yaml'
    save_json(destination, metadata)  # JSON is also valid YAML.
    return destination


def training_args(args: argparse.Namespace, data: Path) -> dict[str, Any]:
    return {
        'data': str(data), 'epochs': args.epochs, 'patience': args.patience,
        'imgsz': 640, 'batch': args.batch, 'device': args.device, 'workers': args.workers,
        'optimizer': 'auto', 'seed': 26, 'deterministic': True,
        'project': str(RUNS), 'name': RUN_NAME, 'exist_ok': False,
        'plots': True, 'save': True, 'cache': False,
        'hsv_h': 0.01, 'hsv_s': 0.25, 'hsv_v': 0.25,
        'degrees': 5.0, 'translate': 0.10, 'scale': 0.30,
        'shear': 0.0, 'perspective': 0.0, 'flipud': 0.0, 'fliplr': 0.0,
        'mosaic': 0.30, 'close_mosaic': 10, 'mixup': 0.0, 'copy_paste': 0.0,
    }


def summarize(metrics: Any) -> dict[str, Any]:
    """Map AP values through framework class indices, never array position."""
    names = {int(k): str(v) for k, v in metrics.names.items()} if isinstance(metrics.names, dict) else dict(enumerate(metrics.names))
    if [names[i] for i in range(len(CLASSES))] != CLASSES:
        raise ValueError('Trained checkpoint names do not match ATLAS.')
    per_class: dict[str, Any] = {name: None for name in CLASSES}
    indices = list(metrics.box.ap_class_index)
    for pos, class_id in enumerate(indices):
        per_class[names[int(class_id)]] = {
            'ap50': float(metrics.box.ap50[pos]),
            'ap50_95': float(metrics.box.ap[pos]),
        }
    return {
        'map50': float(metrics.box.map50), 'map50_95': float(metrics.box.map),
        'precision': float(metrics.box.mp), 'recall': float(metrics.box.mr),
        'per_class': per_class,
        'server_speed_ms_per_image': {str(k): float(v) for k, v in metrics.speed.items()},
        'precision_recall_note': 'Framework max-F1 operating point; do not assume these are ATLAS live thresholds.',
        'speed_note': 'Measured on the coach computer, not the Jetson or full camera pipeline.',
    }


def return_archive(run_dir: Path) -> Path:
    checkpoint = run_dir / 'weights' / 'best.pt'
    if not checkpoint.is_file():
        raise FileNotFoundError(f'Missing checkpoint: {checkpoint}')
    destination = ROOT / 'ATLAS-v6-trained-results.zip'
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.write(checkpoint, 'ATLAS-v6-trained-results/best.pt')
        for folder in [run_dir, RUNS / f'{RUN_NAME}-test-640', RUNS / f'{RUN_NAME}-test-416']:
            if folder.exists():
                for path in sorted(folder.iterdir()):
                    if path.is_file() and path.suffix.lower() in {'.json', '.csv', '.yaml', '.png'}:
                        z.write(path, f'ATLAS-v6-trained-results/{folder.name}/{path.name}')
        for name in ['dataset_preparation.json', 'dataset_manifest.json', 'DATASET_REVIEW.md', 'README.md', 'train.py', 'requirements.txt']:
            z.write(ROOT / name, f'ATLAS-v6-trained-results/provenance/{name}')
    return destination


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true', help='Verify all images, labels, hashes and splits without training.')
    parser.add_argument('--epochs', type=int, default=300, help='Maximum; early stopping can finish earlier.')
    parser.add_argument('--patience', type=int, default=20, help='Stop after this many epochs without validation improvement.')
    parser.add_argument('--batch', type=int, default=-1, help='-1 automatically chooses a single-GPU batch size; lower this if memory is tight.')
    parser.add_argument('--workers', type=int, default=0 if os.name == 'nt' else 4,
                        help='Data-loader processes; defaults to 0 on Windows to avoid shared-memory/page-file failures.')
    parser.add_argument('--device', default='0', help='NVIDIA GPU number; use cpu only if deliberately training on CPU.')
    parser.add_argument('--resume', action='store_true', help='Continue an interrupted run using last.pt.')
    parser.add_argument('--evaluate-only', action='store_true', help='Evaluate existing best.pt and create the return ZIP; do not retrain.')
    parser.add_argument('--base-weights', type=Path, help='Offline copy of the official pretrained yolo26n.pt; never an old ATLAS checkpoint.')
    args = parser.parse_args(argv)
    if args.epochs < 1 or args.patience < 1 or args.workers < 0 or args.batch == 0 or args.batch < -1:
        parser.error('epochs/patience/batch must be positive (batch -1 is allowed), workers >= 0.')
    if args.resume and args.evaluate_only:
        parser.error('--resume and --evaluate-only cannot be combined.')
    if ',' in args.device:
        parser.error('This handoff targets one GPU. Select its number, e.g. --device 1.')
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.base_weights:
        args.base_weights = args.base_weights.resolve()
    report = preflight()
    print('Dataset checks passed:')
    for split, stats in report['splits'].items():
        print(f"  {split}: {stats['images']} images, {stats['boxes']} boxes, {stats['negative_images']} negatives")
    if args.check_only:
        print('No training started. See DATASET_REVIEW.md for remaining limitations.')
        return 0
    if not (3, 10) <= sys.version_info[:2] <= (3, 12):
        raise RuntimeError('Use Python 3.10, 3.11 or 3.12; Python 3.11 is recommended.')
    try:
        import torch
        import ultralytics
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError('Install requirements.txt inside your CUDA-enabled Python environment. See README.md.') from exc
    if ultralytics.__version__ != ULTRALYTICS_VERSION:
        raise RuntimeError(f'Use ultralytics=={ULTRALYTICS_VERSION}; found {ultralytics.__version__}. Install requirements.txt.')
    if args.device != 'cpu':
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA is unavailable. Install the GPU version of PyTorch from https://pytorch.org/get-started/locally/ in this environment. Training was not started. See README.md.')
        index = int(args.device.replace('cuda:', ''))
        if index < 0 or index >= torch.cuda.device_count():
            raise RuntimeError(f'GPU {index} does not exist; choose --device 0 or another available GPU.')
    os.chdir(ROOT)
    run_dir = RUNS / RUN_NAME
    best_path = run_dir / 'weights' / 'best.pt'
    last_path = run_dir / 'weights' / 'last.pt'
    if run_dir.exists() and not (args.resume or args.evaluate_only):
        raise RuntimeError('A run already exists. Use --resume if interrupted, or --evaluate-only if training finished. Keep the saved checkpoint.')
    if args.resume and not last_path.is_file():
        raise FileNotFoundError('No last.pt checkpoint to resume.')
    if args.evaluate_only and not best_path.is_file():
        raise FileNotFoundError('No best.pt checkpoint to evaluate.')
    if args.base_weights and not args.base_weights.resolve().is_file():
        raise FileNotFoundError(f'Missing offline pretrained checkpoint: {args.base_weights}')
    data = resolved_dataset()
    environment = {
        'python': platform.python_version(), 'platform': platform.platform(),
        'ultralytics': ultralytics.__version__, 'torch': torch.__version__,
        'torch_cuda': torch.version.cuda, 'device': args.device,
        'gpu': None if args.device == 'cpu' else torch.cuda.get_device_name(int(args.device.replace('cuda:', ''))),
        'checkpoint_base': str(args.base_weights.resolve()) if args.base_weights else 'official pretrained yolo26n.pt',
    }
    save_json(RUNS / 'preflight.json', report)
    if not args.evaluate_only:
        if args.resume:
            model = YOLO(str(last_path), task='detect')
            model.train(resume=True, device=args.device, workers=args.workers)
        else:
            base = str(args.base_weights.resolve()) if args.base_weights else 'yolo26n.pt'
            model = YOLO(base, task='detect')
            model.train(**training_args(args, data))
    if not best_path.is_file():
        raise FileNotFoundError(f'Trainer did not save expected best.pt: {best_path}')
    best = YOLO(str(best_path), task='detect')
    evaluation = {
        'checkpoint_sha256': sha256(best_path), 'model': 'YOLO26 Nano',
        'environment': environment, 'dataset': report,
        'training_note': 'One training run. Best checkpoint selected on validation only; test evaluated afterward.',
        'deployment_note': 'Build TensorRT on the Jetson after checking this .pt on real XIAO-camera frames.',
    }
    for size in [640, 416]:
        metrics = best.val(data=str(data), split='test', imgsz=size,
                           batch=8, device=args.device, workers=args.workers,
                           project=str(RUNS), name=f'{RUN_NAME}-test-{size}',
                           exist_ok=True, plots=True, verbose=True)
        evaluation[f'test_{size}'] = summarize(metrics)
        # Save after each evaluation so a later interruption does not lose it.
        save_json(run_dir / 'atlas_evaluation.json', evaluation)
    save_json(run_dir / 'environment.json', environment)
    save_json(run_dir / 'preflight.json', report)
    with (run_dir / 'class_results.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['class', 'test_boxes', 'ap50_640', 'ap50_95_640', 'ap50_416', 'ap50_95_416'])
        for name in CLASSES:
            values = []
            for size in [640, 416]:
                values.extend((evaluation[f'test_{size}']['per_class'][name] or {}).get(k) for k in ['ap50', 'ap50_95'])
            writer.writerow([name, report['splits']['test']['class_boxes'][name], *values])
    archive = return_archive(run_dir)
    print(f'Finished. Send this file back to ATLAS: {archive}')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nInterrupted. If runs/yolo26n-atlas-v6/weights/last.pt exists, continue with python train.py --resume.', file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f'\nSTOPPED: {exc}', file=sys.stderr)
        print('If training completed but evaluation failed, use python train.py --evaluate-only.', file=sys.stderr)
        raise SystemExit(1)
