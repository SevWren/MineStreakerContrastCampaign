## **Example Commands**:  Commands to utilize different features of native Iter9 image-sweep mode to obtain different results for different reasons:


```powershell
D:\Github\MineSweepResearchFilesFinalIteration
```

---

## 1. Image-sweep, width 450, seed 11, explicit batch output root

This runs native image-sweep mode on all PNG files directly under `assets/`, writing one batch root with one child run per image.

```powershell
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 450 --seed 11 --allow-noncanonical --run-tag "assets_w450_s11" --out-root "results/iter9/sweep_assets_w450_s11"
```

---

## 2. Image-sweep, width 300, seed 11

This makes smaller boards for discovered images. Smaller boards usually run faster, but can lose some fine detail.

```powershell
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 300 --seed 11 --allow-noncanonical --run-tag "assets_w300_s11" --out-root "results/iter9/sweep_assets_w300_s11"
```

---

## 3. Image-sweep, width 600, seed 11

This makes larger boards for discovered images. Larger boards can capture more detail, but take longer.

```powershell
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 600 --seed 11 --allow-noncanonical --run-tag "assets_w600_s11" --out-root "results/iter9/sweep_assets_w600_s11"
```

---

## 4. Image-sweep, width 450, seed 22

This keeps board size fixed at 450 but changes the random seed.

```powershell
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 450 --seed 22 --allow-noncanonical --run-tag "assets_w450_s22" --out-root "results/iter9/sweep_assets_w450_s22"
```

---

## 5. Image-sweep, width 450, seed 33

This is another fixed-width sweep with a different seed for consistency comparisons.

```powershell
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 450 --seed 33 --allow-noncanonical --run-tag "assets_w450_s33" --out-root "results/iter9/sweep_assets_w450_s33"
```

---

## 6. Image-sweep seed sweep (11 / 22 / 33) at width 450

This runs three batch sweeps at the same board size, changing only seed.

```powershell
foreach ($seed in 11,22,33) { python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 450 --seed $seed --allow-noncanonical --run-tag "assets_w450_s$seed" --out-root "results/iter9/sweep_assets_w450_s$seed" }
```

---

## 7. Image-sweep width sweep (300 / 450 / 600) at seed 11

This runs three batch sweeps with fixed seed and varying board width.

```powershell
foreach ($w in 300,450,600) { python run_iter9.py --image-dir assets --image-glob "*.png" --board-w $w --seed 11 --allow-noncanonical --run-tag "assets_w${w}_s11" --out-root "results/iter9/sweep_assets_w${w}_s11" }
```

---

## 8. Image-sweep width + seed sweep matrix

This is a larger experiment: three widths times three seeds.

```powershell
foreach ($w in 300,450,600) { foreach ($seed in 11,22,33) { python run_iter9.py --image-dir assets --image-glob "*.png" --board-w $w --seed $seed --allow-noncanonical --run-tag "assets_w${w}_s$seed" --out-root "results/iter9/sweep_assets_w${w}_s$seed" } }
```

---

## 9. Recursive image-sweep (include nested folders)

This includes PNG files in subfolders under `assets/`.

```powershell
python run_iter9.py --image-dir assets --image-glob "*.png" --recursive --board-w 450 --seed 11 --allow-noncanonical --run-tag "assets_recursive_w450_s11" --out-root "results/iter9/sweep_assets_recursive_w450_s11"
```

---

## 10. Image-sweep with max-images limit

This runs only the first N discovered images after deterministic sorting.

```powershell
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 450 --seed 11 --allow-noncanonical --max-images 5 --run-tag "assets_top5_w450_s11" --out-root "results/iter9/sweep_assets_top5_w450_s11"
```

---

## 11. Image-sweep with continue-on-error

If one image fails, sweep continues with remaining images and records failures in summary rows.

```powershell
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 450 --seed 11 --allow-noncanonical --continue-on-error --run-tag "assets_continue_on_error_w450_s11" --out-root "results/iter9/sweep_assets_continue_on_error_w450_s11"
```

---

## 12. Image-sweep fail-fast (default behavior)

This uses default fail-fast behavior: the first failed child ends the sweep.

```powershell
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 450 --seed 11 --allow-noncanonical --run-tag "assets_fail_fast_w450_s11" --out-root "results/iter9/sweep_assets_fail_fast_w450_s11"
```

---

## 13. Image-sweep skip-existing for resume/retry

This skips child runs when expected metrics already exist in child directories.

```powershell
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 450 --seed 11 --allow-noncanonical --skip-existing --run-tag "assets_skip_existing_w450_s11" --out-root "results/iter9/sweep_assets_skip_existing_w450_s11"
```

---

## 14. Image-sweep with default out-root behavior

When `--out-root` is omitted, the batch writes under `results/iter9/<batch_id>/`.

```powershell
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 450 --seed 11 --allow-noncanonical --run-tag "assets_default_out_root_w450_s11"
```

---

## 15. Timestamped image-sweep output root

This isolates each batch sweep under a timestamped root for cleaner run history.

```powershell
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"; python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 450 --seed 11 --allow-noncanonical --run-tag "assets_w450_s11_$stamp" --out-root "results/iter9/$stamp/sweep_assets_w450_s11"
```

---

## 16. Filtered image-sweep by filename pattern

This targets only files whose names match a specific pattern.

```powershell
python run_iter9.py --image-dir assets --image-glob "*research*.png" --board-w 450 --seed 11 --allow-noncanonical --run-tag "assets_research_only_w450_s11" --out-root "results/iter9/sweep_assets_research_only_w450_s11"
```

---

## 17. Preflight image integrity checks, then sweep

This first validates a known source image with `image_guard`, then runs sweep mode.

```powershell
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical; if ($LASTEXITCODE -eq 0) { python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 450 --seed 11 --allow-noncanonical --run-tag "assets_prevalidated_w450_s11" --out-root "results/iter9/sweep_assets_prevalidated_w450_s11" }
```

---

## 18. Quick smoke sweep (2 images)

This is a fast smoke run for command-path and summary validation.

```powershell
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 300 --seed 11 --allow-noncanonical --max-images 2 --run-tag "assets_smoke_top2_w300_s11" --out-root "results/iter9/sweep_assets_smoke_top2_w300_s11"
```

---

## 19. Inspect summary JSON after sweep

This prints key summary counts for fast verification.

```powershell
$summary = Get-Content -Raw "results/iter9/sweep_assets_w450_s11/iter9_image_sweep_summary.json" | ConvertFrom-Json; $summary | Select-Object schema_version, images_discovered, rows_recorded, runs_attempted, runs_succeeded, runs_failed, runs_skipped
```

---

## 20. Inspect summary CSV and Markdown after sweep

This checks the CSV header and previews the Markdown summary table.

```powershell
Get-Content "results/iter9/sweep_assets_w450_s11/iter9_image_sweep_summary.csv" -TotalCount 1; Get-Content "results/iter9/sweep_assets_w450_s11/iter9_image_sweep_summary.md" -TotalCount 30
```
