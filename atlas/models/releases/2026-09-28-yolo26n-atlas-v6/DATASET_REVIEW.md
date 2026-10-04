# Inspection of the supplied futureinnovators v6 export

## What the original archive contains

The archive contains 1,710 readable 640x640 images and 3,700 annotation boxes:
1,283 training images, 257 validation images and 170 test images.
The export metadata specifies Auto-Orient and Fit with black edges, with no
Roboflow image augmentations. There are 103/16/16 negative images in those splits.
All seven classes appear in every split. No malformed coordinates, unmatched
annotation files, identical file hashes or identical decoded image hashes were
found. The archive repeats data.yaml three times with identical contents.

## Problems found in v6

- Original source filenames repeat in 108 pairs/groups. Of these, 27 span more
  than one original split. A repeated name is a warning about related input;
  the files are not byte-identical. Keeping those names in one split avoids
  treating transformed/re-encoded versions as independent examples.
- Visual inspection confirms very similar adjacent shots of the same artwork
  arrangements occur in different splits. A simple dHash/thumbnail screen found
  77 cross-split candidate pairs in the original export. That is a screening
  result, not a claim that all 77 pairs are identical photographs.
- Some single artworks have two nearly overlapping boxes with the same class.
  All high-overlap removals in the coach copy are logged.
- Many images use the same rooms, printed reproductions and artwork layouts.
  More photographs do not necessarily mean more independent viewing conditions.
- Four classes have substantially more training examples than Mona Lisa,
  Tutankhamun's mask and Starry Night. No extra synthetic artwork images were
  generated for this package.

## The separate prepared coach copy

| Split | Images | Negative images | Boxes |
| --- | ---: | ---: | ---: |
| Train | 989 | 79 | 2,341 |
| Validation | 324 | 34 | 514 |
| Test | 233 | 22 | 343 |
| Total | 1,546 | 135 | 3,198 |

Preparation:

1. Kept image bytes and the numeric class order unchanged. Changed only the
   names `liberty` -> `liberty_leading_the_people` and
   `pharaoh_mask` -> `tutankhamun_mask` to match ATLAS.
2. Assigned capture-number ranges together, and grouped the late background
   photographs by minute. Capture IDs/timestamps are proxies for related
   captures, not verified session metadata.
3. Excluded 137 image files in capture-boundary buffers and 27 files similar
   to higher-priority held-out examples or their immediate neighbours.
   All 164 exclusions exist in the untouched source ZIP. No source photographs
   were deleted. There are 655 retained images whose split changed.
4. Suppressed 168 duplicate annotation boxes across the full export where the
   class matched and box IoU was at least 0.90, retaining the first original
   box. Some of those images were subsequently excluded. Geometry of the
   retained boxes was not averaged or otherwise changed.
5. Rechecked the prepared images across splits. Source/capture groups are
   confined to one split. The same dHash/thumbnail screen found no remaining
   candidate pairs across the prepared splits.

The 3,198 final boxes therefore reflect both excluded image annotations and
duplicate-box suppression; subtracting 168 alone from 3,700 is not the final
box count. Full details and the original archive hash are in the JSON reports.

## Coverage of each artwork in the prepared copy

Counts below are annotation boxes, not unique camera sessions.

| Class | Train | Validation | Test |
| --- | ---: | ---: | ---: |
| girl_with_a_pearl_earring | 475 | 91 | 40 |
| great_wave_off_kanagawa | 430 | 96 | 70 |
| liberty_leading_the_people | 453 | 103 | 54 |
| mona_lisa | 178 | 72 | 40 |
| tutankhamun_mask | 167 | 37 | 52 |
| starry_night | 173 | 36 | 49 |
| sunflowers | 465 | 79 | 38 |

## Limits of the conclusion

The prepared copy is ready for an offline training experiment. Its test set is
more conservative than the original random split, but it is not an independent
museum or real-headset field trial. Perceptual screening can miss related images,
and camera-session metadata was not supplied. Printed works, backgrounds and
rooms still recur. Do not present internal mAP as guaranteed live ATLAS accuracy.

After this run, the highest-value validation is fresh XIAO-camera footage at
real wearing height, with glare, distance, oblique views, motion blur, partial
artwork and unrelated paintings/backgrounds. Do not tune model choices using
the final test set repeatedly.
