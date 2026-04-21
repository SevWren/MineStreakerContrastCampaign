# Saturation Study Run Matrix + Mandatory Visual Approval Gate

This is the exact run matrix for a full SA3x-only campaign.
All commands below are source-of-truth command blocks.

## Phase Index
- Phase 0: Setup.
- Phase 1A: Fine contrast sweep.
- Phase 1B: Low-end floor sweep.
- Phase 1C: Select top 4 contrasts.
- Phase 2A: Multi-seed repeats on `irisd3`.
- Phase 2B: Control reruns for top contrasts.
- Phase 3A: Piecewise sweep screen.
- Phase 3B: Select top piecewise + multi-seed repeat.
- Phase 4: Adaptive local-cap ablation.
- Phase 5: Control reruns for Phase 4 winner.
- Phase 6: Stress follow-up (`board-w` 362 and 428).
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

## Phase 2A: Multi-seed repeats on irisd3 for top contrasts
```powershell
$TOP = (Get-Content "$ROOT/p01_top_contrasts.txt").Split(",")
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
      --adaptive-local-clusters-per-step 25 --adaptive-local-sa-budget-s 12
  }
}
```

## Phase 2B: Control reruns for each top contrast
```powershell
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
        --adaptive-local-clusters-per-step 25 --adaptive-local-sa-budget-s 12
    }
  }
}
```

## Phase 3A: Piecewise sweep screen (top 2 contrasts, seed 42)
```powershell
$TOP2 = $TOP[0..1]
$KNEES = @(3.6,4.0,4.4)
$TMAXS = @(5.2,5.6,6.0,6.4)
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
        --adaptive-local-clusters-per-step 25 --adaptive-local-sa-budget-s 12
    }
  }
}
```

## Phase 3B: Select top 4 piecewise combos, then multi-seed repeat
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
      --adaptive-local-clusters-per-step 25 --adaptive-local-sa-budget-s 12
  }
}
```

## Phase 4: Adaptive local-cap ablation (best contrast+piecewise, 5 seeds)
```powershell
$BEST_C = "2.0"; $BEST_K = "4.0"; $BEST_T = "6.0"
$MODES = @(
  @{name="nolocal"; flags=@()},
  @{name="fixed46"; flags=@("--adaptive-local-cap","--adaptive-local-cap-ladder","4.6","--adaptive-local-cap-value","4.6","--adaptive-local-trigger-eval","7.5","--adaptive-local-clusters-per-step","25","--adaptive-local-sa-budget-s","12")},
  @{name="ladder_std"; flags=@("--adaptive-local-cap","--adaptive-local-cap-ladder","5.4,5.0,4.8,4.6","--adaptive-local-cap-value","4.6","--adaptive-local-trigger-eval","7.5","--adaptive-local-clusters-per-step","25","--adaptive-local-sa-budget-s","12")},
  @{name="ladder_aggr"; flags=@("--adaptive-local-cap","--adaptive-local-cap-ladder","5.0,4.8,4.6,4.4","--adaptive-local-cap-value","4.4","--adaptive-local-trigger-eval","7.5","--adaptive-local-clusters-per-step","25","--adaptive-local-sa-budget-s","12")},
  @{name="ladder_cons"; flags=@("--adaptive-local-cap","--adaptive-local-cap-ladder","5.6,5.2,4.8,4.6","--adaptive-local-cap-value","4.6","--adaptive-local-trigger-eval","7.5","--adaptive-local-clusters-per-step","25","--adaptive-local-sa-budget-s","12")}
)
foreach($m in $MODES){
  foreach($s in $SEEDS){
    $tag = "sat_p04_irisd3_$($m.name)_s$s"
    $cmd = @(
      "run_iris3d_visual_report.py","--image","irisd3.png","--out-dir","$ROOT/p04_localcap/$tag","--run-tag",$tag,
      "--board-w","300","--seed",$s,"--iters-multiplier","0.25","--max-runtime-s","50",
      "--phase1-budget-s","8","--phase2-budget-s","20",
      "--contrast-factor",$BEST_C,"--pw-knee",$BEST_K,"--pw-t-max",$BEST_T,
      "--hi-boost","18","--method-test-sa-3x","--allow-noncanonical"
    ) + $m.flags
    python @cmd
  }
}
```

## Phase 5: Control reruns for winning Phase 4 mode
```powershell
# Use winner mode flags + BEST_C/BEST_K/BEST_T
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
      --adaptive-local-clusters-per-step 25 --adaptive-local-sa-budget-s 12
  }
}
```

## Phase 6: Stress follow-up on both widths 362 and 428
```powershell
$WIDTHS=@(362,428)
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
      --adaptive-local-clusters-per-step 25 --adaptive-local-sa-budget-s 12
  }
}
```

## Phase 7: Mandatory user visual approval gate
```powershell
@'
candidate_id,phase,metrics_path,visual_path,board_w,seed_mode,user_approved,rejection_reason,reviewer,reviewed_at_utc
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
