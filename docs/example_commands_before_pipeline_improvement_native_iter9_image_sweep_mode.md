## **Example Commands**:  Commands to utilize different features of the pipeline to obtain different results for different reasons:


```powershell
D:\Github\MineSweepResearchFilesFinalIteration
```

---

## 1. Iter9, width 450, seed 11, explicit per-image output folder

This runs the main board-making pipeline once for each of the 9 images. Each image gets its own clearly named results folder, so the outputs are easier to find later.

```powershell
for ($i = 1; $i -le 9; $i++) { python run_iter9.py --image "assets/input_source_image_research_irl$i.png" --board-w 450 --seed 11 --allow-noncanonical --run-tag "research_irl$i_w450_s11" --out-dir "results/iter9/research_irl$i_w450_s11" }
```

---

## 2. Iter9, width 300, seed 11

This makes one smaller board for each image. Smaller boards usually run faster, but they have less space to capture fine image details.

```powershell
for ($i = 1; $i -le 9; $i++) { python run_iter9.py --image "assets/input_source_image_research_irl$i.png" --board-w 300 --seed 11 --allow-noncanonical --run-tag "research_irl$i_w300_s11" }
```

---

## 3. Iter9, width 600, seed 11

This makes one larger board for each image. Larger boards can capture more detail, but they take much longer and use more computer power.

```powershell
for ($i = 1; $i -le 9; $i++) { python run_iter9.py --image "assets/input_source_image_research_irl$i.png" --board-w 600 --seed 11 --allow-noncanonical --run-tag "research_irl$i_w600_s11" }
```

---

## 4. Iter9, width 450, seed 22

This runs the same 450-width board size, but with seed `22` instead of seed `11`. A different seed means the program starts from a different random mine layout.

```powershell
for ($i = 1; $i -le 9; $i++) { python run_iter9.py --image "assets/input_source_image_research_irl$i.png" --board-w 450 --seed 22 --allow-noncanonical --run-tag "research_irl$i_w450_s22" }
```

---

## 5. Iter9, width 450, seed 33

This is another 450-width run, but with seed `33`. It gives a third version of each image’s board, useful for comparing consistency.

```powershell
for ($i = 1; $i -le 9; $i++) { python run_iter9.py --image "assets/input_source_image_research_irl$i.png" --board-w 450 --seed 33 --allow-noncanonical --run-tag "research_irl$i_w450_s33" }
```

---

## 6. Iter9, seed sweep 11 / 22 / 33 at width 450

This runs each image three times at the same board size. The only thing changing is the seed: `11`, `22`, and `33`.

```powershell
foreach ($seed in 11,22,33) { for ($i = 1; $i -le 9; $i++) { python run_iter9.py --image "assets/input_source_image_research_irl$i.png" --board-w 450 --seed $seed --allow-noncanonical --run-tag "research_irl$i_w450_s$seed" } }
```

---

## 7. Iter9, width sweep 300 / 450 / 600 at seed 11

This runs each image at three board sizes. The seed stays the same, so the main thing being tested is board size.

```powershell
foreach ($w in 300,450,600) { for ($i = 1; $i -le 9; $i++) { python run_iter9.py --image "assets/input_source_image_research_irl$i.png" --board-w $w --seed 11 --allow-noncanonical --run-tag "research_irl$i_w${w}_s11" } }
```

---

## 8. Iter9, width + seed sweep

This is the biggest Iter9 test in the list. It runs every image at three widths and three seeds.

```powershell
foreach ($w in 300,450,600) { foreach ($seed in 11,22,33) { for ($i = 1; $i -le 9; $i++) { python run_iter9.py --image "assets/input_source_image_research_irl$i.png" --board-w $w --seed $seed --allow-noncanonical --run-tag "research_irl$i_w${w}_s$seed" } } }
```

---

## 9. Image integrity validation only

This does not create any boards. It only checks that each image file exists, opens correctly, and passes the image safety checks.

```powershell
for ($i = 1; $i -le 9; $i++) { python assets/image_guard.py --path "assets/input_source_image_research_irl$i.png" --allow-noncanonical }
```

---

## 10. Validate each image, then run Iter9 only if validation passes

This first checks each image. If an image passes, it then makes a board for that image.

```powershell
for ($i = 1; $i -le 9; $i++) { python assets/image_guard.py --path "assets/input_source_image_research_irl$i.png" --allow-noncanonical; if ($LASTEXITCODE -eq 0) { python run_iter9.py --image "assets/input_source_image_research_irl$i.png" --board-w 450 --seed 11 --allow-noncanonical --run-tag "research_irl$i_validated_w450_s11" } }
```

---

## 11. Iter9 with per-image manifest validation

This runs Iter9, but each image must match its own manifest file. A manifest is like an ID card for the image.

```powershell
for ($i = 1; $i -le 9; $i++) { python run_iter9.py --image "assets/input_source_image_research_irl$i.png" --image-manifest "assets/input_source_image_research_irl$i_manifest.json" --board-w 450 --seed 11 --run-tag "research_irl$i_manifest_w450_s11" }
```

---

## 12. Iter9 with timestamped output root

This makes results folders with the current date and time in the path. That keeps each batch of runs separate from earlier batches.

```powershell
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"; for ($i = 1; $i -le 9; $i++) { python run_iter9.py --image "assets/input_source_image_research_irl$i.png" --board-w 450 --seed 11 --allow-noncanonical --run-tag "research_irl$i_w450_s11_$stamp" --out-dir "results/iter9/$stamp/research_irl$i_w450_s11" }
```

---

## 13. Benchmark mode, one width, one seed

This uses the benchmark runner instead of the main Iter9 runner. It runs one board size and one seed for each image, then writes benchmark-style summaries.

```powershell
for ($i = 1; $i -le 9; $i++) { python run_benchmark.py --image "assets/input_source_image_research_irl$i.png" --widths 450 --seeds 11 --allow-noncanonical --out-dir "results/benchmark/research_irl$i_w450_s11" }
```

---

## 14. Benchmark mode, width sweep 300 / 450 / 600, seed 11

This tests three board sizes for each image using benchmark mode. The seed stays the same, so the comparison focuses on board width.

```powershell
for ($i = 1; $i -le 9; $i++) { python run_benchmark.py --image "assets/input_source_image_research_irl$i.png" --widths 300 450 600 --seeds 11 --allow-noncanonical --out-dir "results/benchmark/research_irl$i_width_sweep_s11" }
```

---

## 15. Benchmark mode, seed sweep 11 / 22 / 33, width 450

This tests three seeds for each image at the same board width. It checks whether results are stable across different random starts.

```powershell
for ($i = 1; $i -le 9; $i++) { python run_benchmark.py --image "assets/input_source_image_research_irl$i.png" --widths 450 --seeds 11 22 33 --allow-noncanonical --out-dir "results/benchmark/research_irl$i_w450_seed_sweep" }
```

---

## 16. Benchmark mode, width + seed matrix

This tests every image across multiple board sizes and multiple seeds. It creates the most complete benchmark comparison in this group.

```powershell
for ($i = 1; $i -le 9; $i++) { python run_benchmark.py --image "assets/input_source_image_research_irl$i.png" --widths 300 450 600 --seeds 11 22 33 --allow-noncanonical --out-dir "results/benchmark/research_irl$i_matrix" }
```

---

## 17. Benchmark mode with fixed regressions included

This runs the image benchmark and also runs the project’s fixed regression checks. Regression checks are like “make sure old important things still work” tests.

```powershell
for ($i = 1; $i -le 9; $i++) { python run_benchmark.py --image "assets/input_source_image_research_irl$i.png" --widths 450 --seeds 11 --allow-noncanonical --include-regressions --out-dir "results/benchmark/research_irl$i_w450_s11_with_regressions" }
```

---

## 18. Benchmark mode with per-image manifest validation

This runs benchmark mode while requiring each image to match its own manifest file. It is stricter than `--allow-noncanonical`.

```powershell
for ($i = 1; $i -le 9; $i++) { python run_benchmark.py --image "assets/input_source_image_research_irl$i.png" --image-manifest "assets/input_source_image_research_irl$i_manifest.json" --widths 450 --seeds 11 --out-dir "results/benchmark/research_irl$i_manifest_w450_s11" }
```

---

## 19. Benchmark mode with default benchmark widths and seeds

This lets `run_benchmark.py` use its built-in default widths and seeds. You do not manually choose the board sizes or seeds in the command.

```powershell
for ($i = 1; $i -le 9; $i++) { python run_benchmark.py --image "assets/input_source_image_research_irl$i.png" --allow-noncanonical --out-dir "results/benchmark/research_irl$i_default_matrix" }
```

---

## 20. Validate each image, then run benchmark only if validation passes

This first checks each image file. If the image passes, it runs benchmark mode for that image.

```powershell
for ($i = 1; $i -le 9; $i++) { python assets/image_guard.py --path "assets/input_source_image_research_irl$i.png" --allow-noncanonical; if ($LASTEXITCODE -eq 0) { python run_benchmark.py --image "assets/input_source_image_research_irl$i.png" --widths 450 --seeds 11 --allow-noncanonical --out-dir "results/benchmark/research_irl$i_validated_w450_s11" } }
```
