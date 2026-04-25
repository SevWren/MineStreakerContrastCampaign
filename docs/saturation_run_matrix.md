# Saturation Study Run Matrix + Mandatory Visual Approval Gate

This is the exact run matrix for a full SA3x-only campaign.
All commands below are source-of-truth command blocks.

## Phase Index
- Phase 0: Setup.
- Phase 1A: Fine contrast sweep.
- Phase 1B: Low-end floor sweep.
- Phase 1C: Select top 4 contrasts.
- Phase 2A: Multi-seed repeats on `irisd3`; parallel unit is `(contrast, seed)`.
- Phase 2B: Control reruns for top contrasts; parallel unit is `(control image, contrast, seed)`.
- Phase 3A: Piecewise sweep screen; parallel unit is `(contrast, pw_knee, pw_t_max)`.
- Phase 3B: Select top piecewise + multi-seed repeat; repeat parallel unit is `(piecewise row, seed)`.
- Phase 4: Adaptive local-cap ablation; parallel unit is `(local-cap mode, seed)`.
- Phase 5: Control reruns for Phase 4 winner; parallel unit is `(control image, seed)`.
- Phase 6: Stress follow-up (`board-w` 362 and 428); parallel unit is `(width, seed)`.
- Phase 7: Mandatory visual approval gate.

## Phase 0: Setup
```powershell
$STAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$ROOT = "results/saturation_matrix_$STAMP"
New-Item -ItemType Directory -Force -Path $ROOT | Out-Null

$SEEDS = @(11,22,33,44,55)
$CTRL_SEEDS = @(11,22)
$CTRL_IMAGES = @("assets/input_source_image.png","assets/input_source_image_research.png")
$env:ROOT_REL = $ROOT.Replace('\','/').Replace('results/','')
$MAX_PARALLEL = 4
$LEDGER_ROOT = "$ROOT/worker_ledgers"
New-Item -ItemType Directory -Force -Path $LEDGER_ROOT | Out-Null
```

## Phase 1A: Fine contrast sweep (irisd3, seed 42)
```powershell
python run_contrast_preprocessing_study.py `
  --images "irisd3.png" `
  --contrasts "1.2,1.3,1.4,1.5,1.6,1.7,1.8,1.9,2.0,2.1,2.2,2.3,2.4,2.5,2.6" `
  --board-w 300 --max-runtime-s 50 --iters-multiplier 0.25 `
  --phase1-budget-s 8 --phase2-budget-s 20 --seed 42 `
  --allow-noncanonical --out-root "$ROOT/p01a_fine_irisd3_seed42"
```

## Phase 1B: Low-end floor sweep (irisd3, seed 42)
```powershell
python run_contrast_preprocessing_study.py `
  --images "irisd3.png" `
  --contrasts "0.4,0.5,0.6,0.7,0.8,0.9,1.0" `
  --board-w 300 --max-runtime-s 50 --iters-multiplier 0.25 `
  --phase1-budget-s 8 --phase2-budget-s 20 --seed 42 `
  --allow-noncanonical --out-root "$ROOT/p01b_floor_irisd3_seed42"
```

## Phase 1C: Select top 4 contrasts by `n_unknown`, `hi_err`, `total_time_s`
```powershell
@'
import csv, os
paths = [
  f"results/{os.environ['ROOT_REL']}/p01a_fine_irisd3_seed42/contrast_study_runs.csv",
  f"results/{os.environ['ROOT_REL']}/p01b_floor_irisd3_seed42/contrast_study_runs.csv",
]
rows=[]
for p in paths:
    with open(p, encoding="utf-8") as f:
        rows += list(csv.DictReader(f))
rows.sort(key=lambda r:(int(float(r["n_unknown"])), float(r["hi_err"]), float(r["total_time_s"])))
top=[]
for r in rows:
    c=f'{float(r["contrast_factor"]):.1f}'
    if c not in top: top.append(c)
    if len(top)==4: break
out=f"results/{os.environ['ROOT_REL']}/p01_top_contrasts.txt"
open(out,"w",encoding="utf-8").write(",".join(top))
print("TOP_CONTRASTS", top)
'@ | python -
```

## Parallel Execution Contract For Phases 2A-6
- Use `Start-Job` or equivalent worker processes with `MAX_PARALLEL=4`.
- Each worker must write to a unique output directory and a unique phase-local ledger path.
- For CPU-heavy parallel batches, prefer explicit thread caps in each worker environment: `NUMBA_NUM_THREADS=2`, `OMP_NUM_THREADS=2`, `MKL_NUM_THREADS=2`, and `OPENBLAS_NUM_THREADS=2`.
- Add `--phase1-max-workers 2` to Phase 2A diagnostic reruns and any future low-contention confirmation batch to avoid nested Phase 1 repair oversubscription.
- Add these arguments to every `run_iris3d_visual_report.py` worker command:
  - `--ledger-jsonl "$LEDGER_ROOT/<phase>/$tag.jsonl"`
  - `--ledger-csv "$LEDGER_ROOT/<phase>/$tag.csv"`
- Wait for all jobs in a phase before running any phase-selection script.
- Treat missing `metrics_*.json` as a failed shard and rerun that exact shard before advancing.
- After a parallel phase completes, merge phase-local ledgers deterministically by filename if a campaign-level ledger is needed.
- Runtime fields now distinguish solve-clock and total-clock budget pressure: `solve_budget_hit`, `total_runtime_budget_hit`, and `post_solve_overhead_s`; the legacy `runtime_budget_hit` remains total-clock based.

Recommended PowerShell job wrapper:
```powershell
$env:NUMBA_NUM_THREADS = "2"
$env:OMP_NUM_THREADS = "2"
$env:MKL_NUM_THREADS = "2"
$env:OPENBLAS_NUM_THREADS = "2"

function Wait-SaturationJobSlot {
  param([System.Collections.ArrayList]$Jobs, [int]$MaxParallel, [string]$Phase)
  while (($Jobs | Where-Object { $_.State -eq "Running" }).Count -ge $MaxParallel) {
    $done = Wait-Job -Job $Jobs -Any
    Receive-Job -Job $done
    if ($done.State -ne "Completed") { throw "$Phase shard failed: $($done.Name)" }
  }
}

function Complete-SaturationJobs {
  param([System.Collections.ArrayList]$Jobs, [string]$Phase)
  Wait-Job -Job $Jobs | Out-Null
  foreach($job in $Jobs) {
    Receive-Job -Job $job
    if ($job.State -ne "Completed") { throw "$Phase shard failed: $($job.Name)" }
  }
  Remove-Job -Job $Jobs
}
```

Worker launch pattern:
```powershell
$jobs = [System.Collections.ArrayList]::new()
foreach($shard in $SHARDS) {
  Wait-SaturationJobSlot -Jobs $jobs -MaxParallel $MAX_PARALLEL -Phase $PHASE
  [void]$jobs.Add((Start-Job -Name $shard.tag -ArgumentList $shard -ScriptBlock {
    param($shard)
    # Run the exact python command for this phase using only values from $shard.
    # Keep --out-dir, --run-tag, --ledger-jsonl, and --ledger-csv unique per shard.
  }))
}
Complete-SaturationJobs -Jobs $jobs -Phase $PHASE
```

## Phase 2A: Multi-seed repeats on irisd3 for top contrasts
Parallel execution: create one worker per `(contrast, seed)`. Start at most `$MAX_PARALLEL` workers, wait for all `p02_irisd3` workers, then summarize Phase 2A before evaluating Phase 2 -> Phase 3 promotion.

```powershell
$TOP = (Get-Content "$ROOT/p01_top_contrasts.txt").Split(",")
New-Item -ItemType Directory -Force -Path "$LEDGER_ROOT/p02_irisd3" | Out-Null
foreach($c in $TOP){
  foreach($s in $SEEDS){
    $tag = "sat_p02_irisd3_c$($c.Replace('.','p'))_s$s"
    python run_iris3d_visual_report.py `
      --image "irisd3.png" --out-dir "$ROOT/p02_irisd3/$tag" `
      --run-tag $tag --board-w 300 --seed $s `
      --iters-multiplier 0.25 --max-runtime-s 50 `
      --phase1-budget-s 8 --phase2-budget-s 20 `
      --pw-knee 4.0 --pw-t-max 6.0 --contrast-factor $c --hi-boost 18 `
      --method-test-sa-3x --allow-noncanonical `
      --adaptive-local-cap --adaptive-local-cap-ladder "5.4,5.0,4.8,4.6" `
      --adaptive-local-cap-value 4.6 --adaptive-local-trigger-eval 7.5 `
      --adaptive-local-clusters-per-step 25 --adaptive-local-sa-budget-s 12 `
      --ledger-jsonl "$LEDGER_ROOT/p02_irisd3/$tag.jsonl" `
      --ledger-csv "$LEDGER_ROOT/p02_irisd3/$tag.csv"
  }
}
```

## Phase 2B: Control reruns for each top contrast
Parallel execution: create one worker per `(control image, contrast, seed)`. Phase 2B can run after `$TOP` is known; it does not need Phase 2A results, but final Phase 2 assessment should wait for both Phase 2A and Phase 2B.

```powershell
New-Item -ItemType Directory -Force -Path "$LEDGER_ROOT/p02_controls" | Out-Null
foreach($img in $CTRL_IMAGES){
  $key = [System.IO.Path]::GetFileNameWithoutExtension($img)
  foreach($c in $TOP){
    foreach($s in $CTRL_SEEDS){
      $tag = "sat_p02_ctrl_${key}_c$($c.Replace('.','p'))_s$s"
      python run_iris3d_visual_report.py `
        --image $img --out-dir "$ROOT/p02_controls/$tag" `
        --run-tag $tag --board-w 300 --seed $s `
        --iters-multiplier 0.25 --max-runtime-s 50 `
        --phase1-budget-s 8 --phase2-budget-s 20 `
        --pw-knee 4.0 --pw-t-max 6.0 --contrast-factor $c --hi-boost 18 `
        --method-test-sa-3x --allow-noncanonical `
        --adaptive-local-cap --adaptive-local-cap-ladder "5.4,5.0,4.8,4.6" `
        --adaptive-local-cap-value 4.6 --adaptive-local-trigger-eval 7.5 `
        --adaptive-local-clusters-per-step 25 --adaptive-local-sa-budget-s 12 `
        --ledger-jsonl "$LEDGER_ROOT/p02_controls/$tag.jsonl" `
        --ledger-csv "$LEDGER_ROOT/p02_controls/$tag.csv"
    }
  }
}
```

## Phase 3A: Piecewise sweep screen (top 2 contrasts, seed 42)
Parallel execution: create one worker per valid `(contrast, pw_knee, pw_t_max)` combination. Run the Phase 3B selector only after every `p03a_piecewise_screen` metrics file exists.

```powershell
$TOP2 = $TOP[0..1]
$KNEES = @(3.6,4.0,4.4)
$TMAXS = @(5.2,5.6,6.0,6.4)
New-Item -ItemType Directory -Force -Path "$LEDGER_ROOT/p03a_piecewise_screen" | Out-Null
foreach($c in $TOP2){
  foreach($k in $KNEES){
    foreach($t in $TMAXS){
      if([double]$t -le [double]$k){ continue }
      $tag = "sat_p03a_irisd3_c$($c.Replace('.','p'))_k$($k.ToString().Replace('.','p'))_t$($t.ToString().Replace('.','p'))_s42"
      python run_iris3d_visual_report.py `
        --image "irisd3.png" --out-dir "$ROOT/p03a_piecewise_screen/$tag" `
        --run-tag $tag --board-w 300 --seed 42 `
        --iters-multiplier 0.25 --max-runtime-s 50 `
        --phase1-budget-s 8 --phase2-budget-s 20 `
        --contrast-factor $c --pw-knee $k --pw-t-max $t --hi-boost 18 `
        --method-test-sa-3x --allow-noncanonical `
        --adaptive-local-cap --adaptive-local-cap-ladder "5.4,5.0,4.8,4.6" `
        --adaptive-local-cap-value 4.6 --adaptive-local-trigger-eval 7.5 `
        --adaptive-local-clusters-per-step 25 --adaptive-local-sa-budget-s 12 `
        --ledger-jsonl "$LEDGER_ROOT/p03a_piecewise_screen/$tag.jsonl" `
        --ledger-csv "$LEDGER_ROOT/p03a_piecewise_screen/$tag.csv"
    }
  }
}
```

## Phase 3B: Select top 4 piecewise combos, then multi-seed repeat
Selection step: serial. Repeat step: parallel by `(piecewise row, seed)`.

```powershell
@'
import csv, json, glob, os
root=f"results/{os.environ['ROOT_REL']}/p03a_piecewise_screen"
rows=[]
for mp in glob.glob(root + "/**/metrics_*.json", recursive=True):
    j=json.load(open(mp, encoding="utf-8"))
    rows.append({
      "contrast": str(j.get("contrast_factor")),
      "pw_knee": str(j.get("pw_knee")),
      "pw_t_max": str(j.get("pw_t_max")),
      "n_unknown": int(j.get("n_unknown",0)),
      "hi_err": float(j.get("hi_err",0.0)),
      "total_time_s": float(j.get("total_time_s",0.0)),
    })
rows.sort(key=lambda r:(r["n_unknown"], r["hi_err"], r["total_time_s"]))
seen=set(); top=[]
for r in rows:
    k=(r["contrast"], r["pw_knee"], r["pw_t_max"])
    if k in seen: continue
    seen.add(k); top.append(r)
    if len(top)==4: break
out=f"results/{os.environ['ROOT_REL']}/p03_top_piecewise.csv"
with open(out,"w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f, fieldnames=["contrast","pw_knee","pw_t_max"])
    w.writeheader()
    for r in top: w.writerow({k:r[k] for k in ["contrast","pw_knee","pw_t_max"]})
print("TOP_PIECEWISE", top)
'@ | python -
```

```powershell
$TOPPW = Import-Csv "$ROOT/p03_top_piecewise.csv"
New-Item -ItemType Directory -Force -Path "$LEDGER_ROOT/p03b_piecewise_repeat" | Out-Null
foreach($row in $TOPPW){
  foreach($s in $SEEDS){
    $c=$row.contrast; $k=$row.pw_knee; $t=$row.pw_t_max
    $tag = "sat_p03b_irisd3_c$($c.Replace('.','p'))_k$($k.Replace('.','p'))_t$($t.Replace('.','p'))_s$s"
    python run_iris3d_visual_report.py `
      --image "irisd3.png" --out-dir "$ROOT/p03b_piecewise_repeat/$tag" `
      --run-tag $tag --board-w 300 --seed $s `
      --iters-multiplier 0.25 --max-runtime-s 50 `
      --phase1-budget-s 8 --phase2-budget-s 20 `
      --contrast-factor $c --pw-knee $k --pw-t-max $t --hi-boost 18 `
      --method-test-sa-3x --allow-noncanonical `
      --adaptive-local-cap --adaptive-local-cap-ladder "5.4,5.0,4.8,4.6" `
      --adaptive-local-cap-value 4.6 --adaptive-local-trigger-eval 7.5 `
      --adaptive-local-clusters-per-step 25 --adaptive-local-sa-budget-s 12 `
      --ledger-jsonl "$LEDGER_ROOT/p03b_piecewise_repeat/$tag.jsonl" `
      --ledger-csv "$LEDGER_ROOT/p03b_piecewise_repeat/$tag.csv"
  }
}
```

## Phase 4: Adaptive local-cap ablation (best contrast+piecewise, 5 seeds)
Parallel execution: create one worker per `(local-cap mode, seed)`. Select the Phase 4 winner only after all five modes have complete 5-seed result sets.

```powershell
$BEST_C = "2.0"; $BEST_K = "4.0"; $BEST_T = "6.0"
$MODES = @(
  @{name="nolocal"; flags=@()},
  @{name="fixed46"; flags=@("--adaptive-local-cap","--adaptive-local-cap-ladder","4.6","--adaptive-local-cap-value","4.6","--adaptive-local-trigger-eval","7.5","--adaptive-local-clusters-per-step","25","--adaptive-local-sa-budget-s","12")},
  @{name="ladder_std"; flags=@("--adaptive-local-cap","--adaptive-local-cap-ladder","5.4,5.0,4.8,4.6","--adaptive-local-cap-value","4.6","--adaptive-local-trigger-eval","7.5","--adaptive-local-clusters-per-step","25","--adaptive-local-sa-budget-s","12")},
  @{name="ladder_aggr"; flags=@("--adaptive-local-cap","--adaptive-local-cap-ladder","5.0,4.8,4.6,4.4","--adaptive-local-cap-value","4.4","--adaptive-local-trigger-eval","7.5","--adaptive-local-clusters-per-step","25","--adaptive-local-sa-budget-s","12")},
  @{name="ladder_cons"; flags=@("--adaptive-local-cap","--adaptive-local-cap-ladder","5.6,5.2,4.8,4.6","--adaptive-local-cap-value","4.6","--adaptive-local-trigger-eval","7.5","--adaptive-local-clusters-per-step","25","--adaptive-local-sa-budget-s","12")}
)
New-Item -ItemType Directory -Force -Path "$LEDGER_ROOT/p04_localcap" | Out-Null
foreach($m in $MODES){
  foreach($s in $SEEDS){
    $tag = "sat_p04_irisd3_$($m.name)_s$s"
    $cmd = @(
      "run_iris3d_visual_report.py","--image","irisd3.png","--out-dir","$ROOT/p04_localcap/$tag","--run-tag",$tag,
      "--board-w","300","--seed",$s,"--iters-multiplier","0.25","--max-runtime-s","50",
      "--phase1-budget-s","8","--phase2-budget-s","20",
      "--contrast-factor",$BEST_C,"--pw-knee",$BEST_K,"--pw-t-max",$BEST_T,
      "--hi-boost","18","--method-test-sa-3x","--allow-noncanonical",
      "--ledger-jsonl","$LEDGER_ROOT/p04_localcap/$tag.jsonl",
      "--ledger-csv","$LEDGER_ROOT/p04_localcap/$tag.csv"
    ) + $m.flags
    python @cmd
  }
}
```

## Phase 5: Control reruns for winning Phase 4 mode
Parallel execution: after the winning Phase 4 mode is fixed, create one worker per `(control image, seed)`. These workers are independent from Phase 6 stress workers if the same winner flags are used.

```powershell
# Use winner mode flags + BEST_C/BEST_K/BEST_T
New-Item -ItemType Directory -Force -Path "$LEDGER_ROOT/p05_controls_winner" | Out-Null
foreach($img in $CTRL_IMAGES){
  $key=[System.IO.Path]::GetFileNameWithoutExtension($img)
  foreach($s in $CTRL_SEEDS){
    $tag = "sat_p05_ctrl_${key}_winner_s$s"
    python run_iris3d_visual_report.py `
      --image $img --out-dir "$ROOT/p05_controls_winner/$tag" --run-tag $tag `
      --board-w 300 --seed $s --iters-multiplier 0.25 --max-runtime-s 50 `
      --phase1-budget-s 8 --phase2-budget-s 20 `
      --contrast-factor $BEST_C --pw-knee $BEST_K --pw-t-max $BEST_T --hi-boost 18 `
      --method-test-sa-3x --allow-noncanonical `
      --adaptive-local-cap --adaptive-local-cap-ladder "5.4,5.0,4.8,4.6" `
      --adaptive-local-cap-value 4.6 --adaptive-local-trigger-eval 7.5 `
      --adaptive-local-clusters-per-step 25 --adaptive-local-sa-budget-s 12 `
      --ledger-jsonl "$LEDGER_ROOT/p05_controls_winner/$tag.jsonl" `
      --ledger-csv "$LEDGER_ROOT/p05_controls_winner/$tag.csv"
  }
}
```

## Phase 6: Stress follow-up on both widths 362 and 428
Parallel execution: after the winning Phase 4 mode is fixed, create one worker per `(width, seed)`. Final promotion waits for all Phase 5 controls and all Phase 6 stress shards.

```powershell
$WIDTHS=@(362,428)
New-Item -ItemType Directory -Force -Path "$LEDGER_ROOT/p06_stress" | Out-Null
foreach($w in $WIDTHS){
  foreach($s in $SEEDS){
    $tag = "sat_p06_irisd3_w${w}_s${s}"
    python run_iris3d_visual_report.py `
      --image "irisd3.png" --out-dir "$ROOT/p06_stress/$tag" --run-tag $tag `
      --board-w $w --seed $s --iters-multiplier 0.25 --max-runtime-s 50 `
      --phase1-budget-s 8 --phase2-budget-s 20 `
      --contrast-factor $BEST_C --pw-knee $BEST_K --pw-t-max $BEST_T --hi-boost 18 `
      --method-test-sa-3x --allow-noncanonical `
      --adaptive-local-cap --adaptive-local-cap-ladder "5.4,5.0,4.8,4.6" `
      --adaptive-local-cap-value 4.6 --adaptive-local-trigger-eval 7.5 `
      --adaptive-local-clusters-per-step 25 --adaptive-local-sa-budget-s 12 `
      --ledger-jsonl "$LEDGER_ROOT/p06_stress/$tag.jsonl" `
      --ledger-csv "$LEDGER_ROOT/p06_stress/$tag.csv"
  }
}
```

## Phase 7: Mandatory user visual approval gate
```powershell
@'
candidate_id,phase,metrics_path,visual_path,board_w,seed_mode,parallel_batch_id,shard_id,user_approved,rejection_reason,reviewer,reviewed_at_utc
'@ | Set-Content "$ROOT/winner_visual_review.csv"
```

- Review top-ranked winner candidate images from Phases 4 and 6.
- Mark `user_approved=yes` only if visual output is acceptable per checklist.
- If rejected, record `rejection_reason`, promote next-ranked candidate, and repeat controls/stress if needed.

## Promotion Rules
- Phase 1 -> Phase 2: top 4 contrasts by `n_unknown`, tie-break `hi_err`, then `total_time_s`.
- Phase 2 -> Phase 3: top 2 by median `n_unknown` across 5 seeds; reject if median runtime > 50s.
- Phase 3 -> Phase 4: top 1 piecewise config by median `n_unknown`; require `hi_err` not worse than +10% vs best Phase 2.
- Phase 4 winner: best median `n_unknown`; ties by `hi_err`, then runtime.
- Final winner requires metric win + control pass + stress pass + visual approval.

## Required Campaign Outputs
- `matrix_runs.csv`
- `matrix_summary.json`
- `matrix_summary.md`
- `winner_visual_review.csv`

Recommended parallel audit fields in generated summaries:
- `parallel_batch_id`
- `shard_id`
- `worker_ledger_jsonl`
- `worker_ledger_csv`
