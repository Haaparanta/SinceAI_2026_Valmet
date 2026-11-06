# Source data inventory

Everything the partner gave us lives in [`Source-Data-Do-Not_change/`](../../Source-Data-Do-Not_change/). Do not edit those files; write derived outputs somewhere else.

| File (as delivered) | Size | In git? | Doc |
|---|---:|:---:|---|
| `Valmet_x_SinceAI_2026_Challenge_Brief_FINAL_updated (1).docx` | 48.5 KB | yes | [challenge-brief/](challenge-brief/README.md) |
| `Valmet_SinceAI_2026_Synthetic_Industrial_Metaverse_Builder_Pack (1) (2) (1).xlsx` | 495 KB | yes | [builder-pack/](builder-pack/README.md) |
| `Industrial Boiler Room (1).ply` | 355 MB | **no** | [boiler-room-ply/](boiler-room-ply/README.md) |
| `Industrial Boiler Room (1).ply.sha256` | 97 B | **no** | checksum for the PLY |
| `Industrial Boiler Room (1).mp4` | 194 MB | **no** | [demo-videos/](demo-videos/README.md) |
| `semantic extraction demo 1 (1).mp4` | 25 MB | **no** | [demo-videos/](demo-videos/README.md) |
| `semantic extraction demo 2 (1).mp4` | 15 MB | **no** | [demo-videos/](demo-videos/README.md) |

## Getting the large files

`*.ply` and `*.mp4` are in [`.gitignore`](../../.gitignore) because GitHub rejects files over 100 MB. Get them from a teammate (or the Since AI Discord) and drop them into `Source-Data-Do-Not_change/` under the exact names above. Then check the scan:

```bash
cd Source-Data-Do-Not_change && shasum -a 256 -c "Industrial Boiler Room (1).ply.sha256"
```

Expected hash: `117195366421b07aa6738415e94609d96cd41993a0c5b8e8b730849f6b7f1b03`.

## Name mismatch

The brief calls the files `Industrial Boiler Room.ply`, `semantic extraction demo 1.mp4` and `Valmet_SinceAI_2026_Synthetic_Industrial_Metaverse_Builder_Pack.xlsx`. The delivered copies carry download suffixes like ` (1)` and ` (1) (2) (1)`. Code should look the files up by glob or a config path, not by the brief's names.

## Derived files in docs

- [`builder-pack/data-reference/`](builder-pack/data-reference/README.md): every row of the small Excel sheets as Markdown tables.
- [`demo-videos/img/`](demo-videos/img/): four small JPEG contact sheets (≈ 550 KB total) made from frames of the three videos. They are derived from partner media; confirm sharing is fine before the repo goes public.

## Missing from the delivery

The pack's `START_HERE` sheet refers to `telemetry_full_14d_30min.csv` (all 20,160 telemetry rows over 14 days) and the `RAG_Corpus_Index` sheet lists 38 `DOC-*.md` files. **Neither the CSV nor the Markdown files were delivered.** The Excel only holds a 3-day telemetry sample (4,320 rows) and eight short core knowledge texts. See [builder-pack/](builder-pack/README.md#gaps-to-plan-around) for how to work around it.
