"""
pipeline.py — Full orchestration.  Iter 2: asymmetric weights + extended schedule.
"""
from __future__ import annotations
import os, sys, json, time, warnings
from dataclasses import dataclass, field
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

try:
    from .core import (compute_N, load_image_smart,
                       compute_edge_weights, compute_asymmetric_weights,
                       assert_board_valid)
    from .corridors import build_adaptive_corridors
    from .sa import compile_sa_kernel, run_sa
    from .repair import run_last100_repair, run_phase1_repair, run_phase2_full_repair, compute_repair_visual_delta
    from .report import render_report
    from .solver import classify_unresolved_clusters, solve_board
except ImportError:
    from core import (compute_N, load_image_smart,
                      compute_edge_weights, compute_asymmetric_weights,
                      assert_board_valid)
    from corridors import build_adaptive_corridors
    from sa import compile_sa_kernel, run_sa
    from repair import run_last100_repair, run_phase1_repair, run_phase2_full_repair, compute_repair_visual_delta
    from report import render_report
    from solver import classify_unresolved_clusters, solve_board


def atomic_save_json(data, path):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f: json.dump(data, f, indent=2)
    os.replace(tmp, path)

def atomic_save_npy(arr, path):
    tmp = path + '.tmp.npy'
    np.save(tmp, arr)
    os.replace(tmp, path)


class RouteStateInvariantError(RuntimeError):
    """Raised when accepted_move_count != n_fixed, indicating log corruption or bug."""
    def __init__(self, field, expected, actual, context):
        self.field = field
        self.expected = expected
        self.actual = actual
        self.context = context
        super().__init__(
            f"Invariant failed: {field} expected {expected}, got {actual}. Context: {context}"
        )


@dataclass
class RepairRoutingConfig:
    phase2_budget_s: float = 360.0
    last100_budget_s: float = 300.0
    last100_unknown_threshold: int = 100
    solve_max_rounds: int = 300
    trial_max_rounds: int = 60
    # Candidate limits for phase2 full repair (lower = faster, fewer repairs)
    max_ext_mines_per_cluster: int = 16
    pair_trial_limit: int = 12
    pair_combo_limit: int = 24
    # Control which repair methods are used during annealing
    enable_phase2: bool = True
    enable_last100: bool = True
    enable_sa_rerun: bool = False


@dataclass
class RepairRouteResult:
    grid: np.ndarray
    sr: object
    selected_route: str
    route_result: str
    failure_taxonomy: dict
    route_outcome_detail: str = "no_late_stage_route_invoked"
    next_recommended_route: object = None

    solver_n_unknown_before: int = 0
    solver_n_unknown_after: int = 0

    phase2_full_repair_hit_time_budget: bool = False
    last100_repair_hit_time_budget: bool = False

    phase2_full_repair_invoked: bool = False
    phase2_full_repair_n_fixed: int = 0
    phase2_full_repair_accepted_move_count: int = 0
    phase2_full_repair_changed_grid: bool = False
    phase2_full_repair_reduced_unknowns: bool = False
    phase2_full_repair_solved: bool = False
    phase2_solver_n_unknown_before: object = None
    phase2_solver_n_unknown_after: object = None

    last100_invoked: bool = False
    last100_n_fixes: int = 0
    last100_accepted_move_count: int = 0
    last100_solver_n_unknown_before: object = None
    last100_solver_n_unknown_after: object = None
    last100_stop_reason: object = None

    phase2_log: list = field(default_factory=list)
    last100_log: list = field(default_factory=list)
    visual_delta_summary: dict = field(default_factory=dict)
    decision: dict = field(default_factory=dict)

    def route_state_fields(self) -> dict:
        return {
            "selected_route": self.selected_route,
            "route_result": self.route_result,
            "route_outcome_detail": self.route_outcome_detail,
            "next_recommended_route": self.next_recommended_route,
            "solver_n_unknown_before": int(self.solver_n_unknown_before),
            "solver_n_unknown_after": int(self.solver_n_unknown_after),
            "phase2_full_repair_invoked": bool(self.phase2_full_repair_invoked),
            "phase2_full_repair_hit_time_budget": bool(self.phase2_full_repair_hit_time_budget),
            "phase2_full_repair_n_fixed": int(self.phase2_full_repair_n_fixed),
            "phase2_full_repair_accepted_move_count": int(self.phase2_full_repair_accepted_move_count),
            "phase2_full_repair_changed_grid": bool(self.phase2_full_repair_changed_grid),
            "phase2_full_repair_reduced_unknowns": bool(self.phase2_full_repair_reduced_unknowns),
            "phase2_full_repair_solved": bool(self.phase2_full_repair_solved),
            "phase2_solver_n_unknown_before": self.phase2_solver_n_unknown_before,
            "phase2_solver_n_unknown_after": self.phase2_solver_n_unknown_after,
            "last100_invoked": bool(self.last100_invoked),
            "last100_repair_hit_time_budget": bool(self.last100_repair_hit_time_budget),
            "last100_n_fixes": int(self.last100_n_fixes),
            "last100_accepted_move_count": int(self.last100_accepted_move_count),
            "last100_solver_n_unknown_before": self.last100_solver_n_unknown_before,
            "last100_solver_n_unknown_after": self.last100_solver_n_unknown_after,
            "last100_stop_reason": self.last100_stop_reason,
        }


ROUTE_STATE_KEYS = {
    "selected_route", "route_result", "route_outcome_detail", "next_recommended_route",
    "solver_n_unknown_before", "solver_n_unknown_after",
    "phase2_full_repair_invoked", "phase2_full_repair_hit_time_budget",
    "phase2_full_repair_n_fixed", "phase2_full_repair_accepted_move_count",
    "phase2_full_repair_changed_grid", "phase2_full_repair_reduced_unknowns",
    "phase2_full_repair_solved", "phase2_solver_n_unknown_before", "phase2_solver_n_unknown_after",
    "last100_invoked", "last100_repair_hit_time_budget",
    "last100_n_fixes", "last100_accepted_move_count",
    "last100_solver_n_unknown_before", "last100_solver_n_unknown_after", "last100_stop_reason",
}


def _build_route_result(
    *,
    grid: np.ndarray,
    sr,
    failure_taxonomy: dict,
    decision: dict,
    phase2_log: list | None = None,
    last100_log: list | None = None,
    visual_delta_summary: dict | None = None,
) -> RepairRouteResult:
    missing = sorted(ROUTE_STATE_KEYS - set(decision))
    if missing:
        raise ValueError(f"Incomplete route decision before result construction: {missing}")

    sr_unknown = int(sr.n_unknown)
    decision_unknown = int(decision["solver_n_unknown_after"])
    if sr_unknown != decision_unknown:
        raise ValueError(
            "Route decision solver_n_unknown_after is stale: "
            f"decision={decision_unknown}, sr={sr_unknown}. "
            "Grid/sr was modified without updating decision."
        )

    if (
        bool(decision["phase2_full_repair_invoked"])
        and not bool(decision["last100_invoked"])
        and decision["selected_route"] != "phase2_full_repair"
    ):
        raise ValueError(
            "Phase 2 invoked but selected_route is not phase2_full_repair. "
            f"selected_route={decision['selected_route']!r}"
        )

    if decision["selected_route"] == "needs_sa_or_adaptive_rerun":
        raise ValueError(
            "needs_sa_or_adaptive_rerun is a next_recommended_route value, "
            "not a selected_route value. This indicates the route state was not updated after Phase 2."
        )

    route = RepairRouteResult(
        grid=grid.copy(),
        sr=sr,
        selected_route=decision["selected_route"],
        route_result=decision["route_result"],
        route_outcome_detail=decision["route_outcome_detail"],
        next_recommended_route=decision["next_recommended_route"],
        solver_n_unknown_before=int(decision["solver_n_unknown_before"]),
        solver_n_unknown_after=decision_unknown,
        failure_taxonomy=dict(failure_taxonomy),
        phase2_full_repair_invoked=bool(decision["phase2_full_repair_invoked"]),
        phase2_full_repair_hit_time_budget=bool(decision["phase2_full_repair_hit_time_budget"]),
        phase2_full_repair_n_fixed=int(decision["phase2_full_repair_n_fixed"]),
        phase2_full_repair_accepted_move_count=int(decision["phase2_full_repair_accepted_move_count"]),
        phase2_full_repair_changed_grid=bool(decision["phase2_full_repair_changed_grid"]),
        phase2_full_repair_reduced_unknowns=bool(decision["phase2_full_repair_reduced_unknowns"]),
        phase2_full_repair_solved=bool(decision["phase2_full_repair_solved"]),
        phase2_solver_n_unknown_before=decision["phase2_solver_n_unknown_before"],
        phase2_solver_n_unknown_after=decision["phase2_solver_n_unknown_after"],
        last100_invoked=bool(decision["last100_invoked"]),
        last100_repair_hit_time_budget=bool(decision["last100_repair_hit_time_budget"]),
        last100_n_fixes=int(decision["last100_n_fixes"]),
        last100_accepted_move_count=int(decision["last100_accepted_move_count"]),
        last100_solver_n_unknown_before=decision["last100_solver_n_unknown_before"],
        last100_solver_n_unknown_after=decision["last100_solver_n_unknown_after"],
        last100_stop_reason=decision["last100_stop_reason"],
        phase2_log=list(phase2_log or []),
        last100_log=list(last100_log or []),
        visual_delta_summary=dict(visual_delta_summary or {}),
        decision=dict(decision),
    )

    for key, value in route.route_state_fields().items():
        if route.decision.get(key) != value:
            raise ValueError(
                f"Route decision disagrees with RepairRouteResult for {key}: "
                f"{route.decision.get(key)!r} != {value!r}"
            )

    return route


def route_late_stage_failure(
    grid: np.ndarray,
    target: np.ndarray,
    weights: np.ndarray,
    forbidden: np.ndarray,
    sr,
    config: RepairRoutingConfig,
) -> RepairRouteResult:
    """
    Choose the cheapest next intervention based on unresolved-cell diagnosis.
    """
    del weights
    failure_taxonomy = classify_unresolved_clusters(grid, sr)

    # 2d: Default decision dict — selected_route starts as "none"
    decision = {
        "solver_n_unknown_before": int(sr.n_unknown),
        "solver_n_unknown_after": int(sr.n_unknown),
        "dominant_failure_class": failure_taxonomy.get("dominant_failure_class"),
        "recommended_route": failure_taxonomy.get("recommended_route"),

        "selected_route": "none",
        "route_result": "unresolved_after_repair",
        "route_outcome_detail": "no_late_stage_route_invoked",
        "next_recommended_route": "needs_sa_or_adaptive_rerun",

        "phase2_budget_s": float(config.phase2_budget_s),
        "last100_budget_s": float(config.last100_budget_s),

        "phase2_full_repair_invoked": False,
        "phase2_full_repair_hit_time_budget": False,
        "phase2_full_repair_n_fixed": 0,
        "phase2_full_repair_accepted_move_count": 0,
        "phase2_full_repair_changed_grid": False,
        "phase2_full_repair_reduced_unknowns": False,
        "phase2_full_repair_solved": False,
        "phase2_solver_n_unknown_before": None,
        "phase2_solver_n_unknown_after": None,

        "last100_invoked": False,
        "last100_repair_hit_time_budget": False,
        "last100_n_fixes": 0,
        "last100_accepted_move_count": 0,
        "last100_solver_n_unknown_before": None,
        "last100_solver_n_unknown_after": None,
        "last100_stop_reason": None,

        "sa_rerun_invoked": False,
    }

    phase2_log = []
    last100_log = []
    visual_delta_summary = {}

    # 2e: Already-solved branch
    if int(sr.n_unknown) == 0:
        decision.update({
            "selected_route": "already_solved",
            "route_result": "solved",
            "route_outcome_detail": "already_solved_before_routing",
            "next_recommended_route": None,
            "solver_n_unknown_after": 0,
        })
        return _build_route_result(
            grid=grid, sr=sr, failure_taxonomy=failure_taxonomy, decision=dict(decision),
        )

    # 2f: Phase 2 branch
    if config.enable_phase2 and int(failure_taxonomy.get("sealed_cluster_count", 0)) > 0:
        phase2_grid_before = grid.copy()
        phase2_unknown_before = int(sr.n_unknown)
        decision["selected_route"] = "phase2_full_repair"
        decision["phase2_full_repair_invoked"] = True
        decision["phase2_solver_n_unknown_before"] = phase2_unknown_before

        phase2_result = run_phase2_full_repair(
            grid,
            target,
            forbidden,
            verbose=True,
            time_budget_s=float(config.phase2_budget_s),
            trial_max_rounds=int(config.trial_max_rounds),
            solve_max_rounds=int(config.solve_max_rounds),
            max_ext_mines_per_cluster=int(config.max_ext_mines_per_cluster),
            pair_trial_limit=int(config.pair_trial_limit),
            pair_combo_limit=int(config.pair_combo_limit),
        )
        routed_grid = phase2_result.grid
        phase2_log = list(phase2_result.log)
        routed_sr = solve_board(routed_grid, max_rounds=int(config.solve_max_rounds), mode="full")

        if routed_sr is None or not getattr(routed_sr, "success", True):
            decision.update({
                "route_result": "unresolved_repair_error",
                "route_outcome_detail": "solver_failure_post_repair",
                "solver_n_unknown_after": phase2_unknown_before,
            })
            return _build_route_result(
                grid=phase2_grid_before, sr=sr, failure_taxonomy=failure_taxonomy,
                decision=dict(decision), phase2_log=phase2_log, last100_log=[],
            )

        phase2_unknown_after = int(routed_sr.n_unknown)
        phase2_accepted_count = sum(1 for e in phase2_log if bool(e.get("accepted", False)))
        phase2_changed_grid = bool(np.any(routed_grid != phase2_grid_before))
        phase2_reduced_unknowns = phase2_unknown_after < phase2_unknown_before
        phase2_solved = phase2_unknown_after == 0

        decision.update({
            "phase2_full_repair_hit_time_budget": bool(phase2_result.phase2_full_repair_hit_time_budget),
            "phase2_full_repair_n_fixed": int(phase2_result.n_fixed),
            "phase2_full_repair_accepted_move_count": int(phase2_accepted_count),
            "phase2_full_repair_changed_grid": phase2_changed_grid,
            "phase2_full_repair_reduced_unknowns": phase2_reduced_unknowns,
            "phase2_full_repair_solved": phase2_solved,
            "phase2_solver_n_unknown_after": phase2_unknown_after,
            "solver_n_unknown_after": phase2_unknown_after,
        })

        if phase2_solved:
            route_result = "solved"
            route_outcome_detail = "phase2_full_repair_solved"
            next_rec = None
        elif phase2_unknown_after < phase2_unknown_before:
            route_result = "unresolved_after_repair"
            route_outcome_detail = "phase2_full_repair_partial_progress_unresolved"
            next_rec = "last100_repair" if config.enable_last100 else "needs_sa_or_adaptive_rerun"
        elif phase2_unknown_after == phase2_unknown_before and phase2_changed_grid:
            route_result = "unresolved_after_repair"
            route_outcome_detail = "phase2_full_repair_no_op"
            next_rec = "last100_repair" if config.enable_last100 else "needs_sa_or_adaptive_rerun"
        elif phase2_accepted_count == 0:
            route_result = "unresolved_after_repair"
            route_outcome_detail = "phase2_full_repair_no_accepted_moves"
            next_rec = "last100_repair" if config.enable_last100 else "needs_sa_or_adaptive_rerun"
        else:
            route_result = "unresolved_after_repair"
            route_outcome_detail = "phase2_full_repair_partial_progress_unresolved"
            next_rec = "last100_repair" if config.enable_last100 else "needs_sa_or_adaptive_rerun"

        decision.update({
            "route_result": route_result,
            "route_outcome_detail": route_outcome_detail,
            "next_recommended_route": next_rec,
        })

        if phase2_solved:
            phase2_visual_delta = compute_repair_visual_delta(phase2_grid_before, routed_grid, target)
            visual_delta_summary = {
                **phase2_visual_delta,
                "summary_scope": "route_phase",
                "route_phase": "phase2_full_repair",
                "selected_route": decision["selected_route"],
                "route_result": decision["route_result"],
                "route_outcome_detail": decision["route_outcome_detail"],
                "next_recommended_route": decision["next_recommended_route"],
                "solver_n_unknown_before": phase2_unknown_before,
                "solver_n_unknown_after": phase2_unknown_after,
                "accepted_move_count": phase2_accepted_count,
                "n_fixed": int(phase2_result.n_fixed),
                "removed_mine_count": int(np.sum((phase2_grid_before == 1) & (routed_grid == 0))),
                "added_mine_count": int(np.sum((phase2_grid_before == 0) & (routed_grid == 1))),
                "visual_quality_improved": bool(phase2_visual_delta["visual_delta"] < 0),
                "solver_progress_improved": bool(phase2_unknown_after < phase2_unknown_before),
            }
            return _build_route_result(
                grid=routed_grid, sr=routed_sr, failure_taxonomy=failure_taxonomy,
                decision=dict(decision), phase2_log=phase2_log, last100_log=[],
                visual_delta_summary=visual_delta_summary,
            )
        else:
            grid = routed_grid
            sr = routed_sr
            vd = compute_repair_visual_delta(phase2_grid_before, routed_grid, target)
            visual_delta_summary = {
                **vd,
                "summary_scope": "route_phase",
                "route_phase": "phase2_full_repair",
                "selected_route": decision["selected_route"],
                "route_result": decision["route_result"],
                "route_outcome_detail": decision["route_outcome_detail"],
                "next_recommended_route": decision["next_recommended_route"],
                "solver_n_unknown_before": phase2_unknown_before,
                "solver_n_unknown_after": phase2_unknown_after,
                "accepted_move_count": phase2_accepted_count,
                "n_fixed": int(phase2_result.n_fixed),
                "removed_mine_count": int(np.sum((phase2_grid_before == 1) & (routed_grid == 0))),
                "added_mine_count": int(np.sum((phase2_grid_before == 0) & (routed_grid == 1))),
                "visual_quality_improved": bool(vd["visual_delta"] < 0),
                "solver_progress_improved": bool(phase2_unknown_after < phase2_unknown_before),
            }

    # 2g: Last100 branch
    if config.enable_last100 and int(sr.n_unknown) <= int(config.last100_unknown_threshold):
        last100_grid_before = grid.copy()
        last100_unknown_before = int(sr.n_unknown)
        decision["selected_route"] = "last100_repair"
        decision["last100_invoked"] = True
        decision["last100_solver_n_unknown_before"] = last100_unknown_before

        last100_result = run_last100_repair(
            grid,
            target,
            target,
            forbidden,
            budget_s=float(config.last100_budget_s),
            trial_max_rounds=int(config.trial_max_rounds),
            solve_max_rounds=int(config.solve_max_rounds),
            verbose=True,
        )
        routed_grid = last100_result.grid
        routed_sr = last100_result.sr
        last100_log = last100_result.move_log
        last100_unknown_after = int(routed_sr.n_unknown)
        last100_accepted_count = sum(1 for e in last100_log if bool(e.get("accepted", False)))

        if routed_sr is None or not getattr(routed_sr, "success", True):
            decision.update({
                "route_result": "unresolved_repair_error",
                "route_outcome_detail": "solver_failure_post_repair",
                "solver_n_unknown_after": last100_unknown_before,
            })
            return _build_route_result(
                grid=last100_grid_before, sr=sr, failure_taxonomy=failure_taxonomy,
                decision=dict(decision), phase2_log=phase2_log, last100_log=last100_log,
            )

        decision.update({
            "last100_repair_hit_time_budget": bool(last100_result.last100_repair_hit_time_budget),
            "last100_n_fixes": int(last100_result.n_fixes),
            "last100_accepted_move_count": int(last100_accepted_count),
            "last100_solver_n_unknown_after": last100_unknown_after,
            "last100_stop_reason": str(last100_result.stop_reason),
            "solver_n_unknown_after": last100_unknown_after,
        })

        if last100_unknown_after == 0:
            route_result = "solved"
            route_outcome_detail = "last100_repair_solved"
            next_rec = None
        elif bool(last100_result.last100_repair_hit_time_budget):
            route_result = "unresolved_after_repair"
            route_outcome_detail = "last100_repair_timeout_unresolved"
            next_rec = "needs_sa_or_adaptive_rerun"
        elif last100_accepted_count > 0 and last100_unknown_after < last100_unknown_before:
            route_result = "unresolved_after_repair"
            route_outcome_detail = "last100_repair_partial_progress_unresolved"
            next_rec = "needs_sa_or_adaptive_rerun"
        else:
            route_result = "unresolved_after_repair"
            route_outcome_detail = "last100_repair_no_accepted_moves"
            next_rec = "needs_sa_or_adaptive_rerun"

        decision.update({
            "route_result": route_result,
            "route_outcome_detail": route_outcome_detail,
            "next_recommended_route": next_rec,
        })

        last100_visual_delta = compute_repair_visual_delta(last100_grid_before, routed_grid, target)
        visual_delta_summary = {
            **last100_visual_delta,
            "summary_scope": "route_phase",
            "route_phase": "last100_repair",
            "selected_route": decision["selected_route"],
            "route_result": decision["route_result"],
            "route_outcome_detail": decision["route_outcome_detail"],
            "next_recommended_route": decision["next_recommended_route"],
            "solver_n_unknown_before": last100_unknown_before,
            "solver_n_unknown_after": last100_unknown_after,
            "accepted_move_count": last100_accepted_count,
            "n_fixed": int(last100_result.n_fixes),
            "removed_mine_count": int(np.sum((last100_grid_before == 1) & (routed_grid == 0))),
            "added_mine_count": int(np.sum((last100_grid_before == 0) & (routed_grid == 1))),
            "visual_quality_improved": bool(last100_visual_delta["visual_delta"] < 0),
            "solver_progress_improved": bool(last100_unknown_after < last100_unknown_before),
        }

        return _build_route_result(
            grid=routed_grid, sr=routed_sr, failure_taxonomy=failure_taxonomy,
            decision=dict(decision), phase2_log=phase2_log, last100_log=last100_log,
            visual_delta_summary=visual_delta_summary,
        )

    # 2h: Final fallback — no route ran (or phase2 ran unresolved and last100 not eligible)
    return _build_route_result(
        grid=grid,
        sr=sr,
        failure_taxonomy=failure_taxonomy,
        phase2_log=phase2_log,
        last100_log=last100_log,
        visual_delta_summary=visual_delta_summary,
        decision=decision,
    )


def write_repair_route_artifacts(
    out_dir: str,
    board_label: str,
    route_result: RepairRouteResult,
    artifact_metadata: dict | None = None,
) -> dict:
    """
    Write failure_taxonomy.json, repair_route_decision.json, visual_delta_summary.json.
    Return artifact paths.
    """
    del board_label
    failure_taxonomy_path = os.path.join(out_dir, "failure_taxonomy.json")
    repair_route_decision_path = os.path.join(out_dir, "repair_route_decision.json")
    visual_delta_summary_path = os.path.join(out_dir, "visual_delta_summary.json")
    failure_taxonomy = dict(route_result.failure_taxonomy)

    # Build decision from route_state_fields() to ensure completeness
    route_state = route_result.route_state_fields()
    repair_route_decision = dict(route_result.decision)
    # Merge route_state_fields into decision (authoritative source)
    repair_route_decision.update(route_state)

    # Completeness guard
    required = {
        "selected_route", "route_result", "route_outcome_detail", "next_recommended_route",
        "solver_n_unknown_before", "solver_n_unknown_after",
    }
    missing = sorted(required - set(repair_route_decision))
    if missing:
        raise ValueError(f"Incomplete repair route decision: missing {missing}")

    # Dataclass-to-decision sync guard
    for key, value in route_state.items():
        if repair_route_decision.get(key) != value:
            raise ValueError(
                f"Repair route decision disagrees with RepairRouteResult for {key}: "
                f"{repair_route_decision.get(key)!r} != {value!r}"
            )

    # Invariant: accepted_move_count == n_fixed for Phase 2
    if route_result.phase2_full_repair_invoked:
        phase2_accepted = sum(1 for e in route_result.phase2_log if e.get("accepted", False))
        if route_result.phase2_full_repair_accepted_move_count != phase2_accepted:
            raise RouteStateInvariantError(
                "phase2_full_repair_accepted_move_count",
                route_result.phase2_full_repair_accepted_move_count,
                phase2_accepted,
                {"context": "Phase 2 accepted count mismatch"},
            )
        if route_result.phase2_full_repair_n_fixed != phase2_accepted:
            raise RouteStateInvariantError(
                "phase2_full_repair_n_fixed",
                route_result.phase2_full_repair_n_fixed,
                phase2_accepted,
                {"context": "Phase 2 n_fixed does not match accepted count"},
            )

    # Invariant: accepted_move_count == n_fixes for Last100
    if route_result.last100_invoked:
        last100_accepted = sum(1 for e in route_result.last100_log if e.get("accepted", False))
        if route_result.last100_accepted_move_count != last100_accepted:
            raise RouteStateInvariantError(
                "last100_accepted_move_count",
                route_result.last100_accepted_move_count,
                last100_accepted,
                {"context": "Last100 accepted count mismatch"},
            )
        if route_result.last100_n_fixes != last100_accepted:
            raise RouteStateInvariantError(
                "last100_n_fixes",
                route_result.last100_n_fixes,
                last100_accepted,
                {"context": "Last100 n_fixes does not match accepted count"},
            )

    visual_delta_summary = dict(route_result.visual_delta_summary)
    if artifact_metadata is not None:
        failure_taxonomy["artifact_metadata"] = dict(artifact_metadata)
        repair_route_decision["artifact_metadata"] = dict(artifact_metadata)
        visual_delta_summary["artifact_metadata"] = dict(artifact_metadata)
    atomic_save_json(failure_taxonomy, failure_taxonomy_path)
    atomic_save_json(repair_route_decision, repair_route_decision_path)
    atomic_save_json(visual_delta_summary, visual_delta_summary_path)
    return {
        "failure_taxonomy": failure_taxonomy_path,
        "repair_route_decision": repair_route_decision_path,
        "visual_delta_summary": visual_delta_summary_path,
    }


def run_board(board_w, board_h, label, sa_fn, img_path, out_dir,
              iter_num=2,
              density=0.22, border=3, seed=42,
              coarse_iters=2_000_000, fine_iters=6_000_000, refine_iters=8_000_000,
              T_coarse_start=10.0, T_fine=3.5, T_refine=2.0,
              alpha_coarse=0.99998, alpha_fine=0.999996, alpha_refine=0.999997,
              T_min=0.001,
              # Iter 2 weight params
              bg_penalty=6.0, hi_boost=8.0, hi_threshold=3.0,
              edge_sigma=1.0, edge_boost=2.0,
              verbose=True):
    """Legacy orchestration path kept for compatibility. Deprecated."""
    warnings.warn(
        "pipeline.run_board() is legacy/deprecated and will be removed in a future cleanup.",
        DeprecationWarning,
        stacklevel=2,
    )

    t_total = time.perf_counter()

    # ── Step 0: guard ────────────────────────────────────────────────────
    from assets.image_guard import verify_source_image
    verify_source_image(img_path, halt_on_failure=True, verbose=verbose)
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(seed)

    # ── Step 1: image + weights ──────────────────────────────────────────
    print(f"\n[{label}] Loading image…", flush=True)
    target  = load_image_smart(img_path, board_w, board_h, invert=True)

    # ITER 2 PRIMARY CHANGE: asymmetric weights
    weights = compute_asymmetric_weights(target,
                                          bg_penalty=bg_penalty,
                                          hi_boost=hi_boost,
                                          hi_threshold=hi_threshold,
                                          edge_sigma=edge_sigma,
                                          edge_boost=edge_boost)
    print(f"  Asymmetric weights: bg_penalty={bg_penalty}  hi_boost={hi_boost}  "
          f"hi_threshold={hi_threshold}", flush=True)
    print(f"  Weight range: [{weights.min():.2f}, {weights.max():.2f}]  "
          f"mean={weights.mean():.3f}", flush=True)
    print(f"  Target range: [{target.min():.2f}, {target.max():.2f}]  "
          f"mean={target.mean():.3f}", flush=True)

    # ── Step 2: corridors ───────────────────────────────────────────────
    print(f"[{label}] Building corridors…", flush=True)
    forbidden, corridor_pct, seeds, mst = build_adaptive_corridors(
        target, border=border, corridor_width=0, low_target_bias=5.5)
    print(f"  corridor_pct={corridor_pct:.1f}%  n_seeds={len(seeds)}", flush=True)

    # ── Step 3: coarse SA ───────────────────────────────────────────────
    cW, cH = max(10, board_w//2), max(8, board_h//2)
    print(f"[{label}] Coarse SA ({cW}×{cH}, {coarse_iters:,} iters)…", flush=True)
    target_c  = load_image_smart(img_path, cW, cH, invert=True)
    weights_c = compute_asymmetric_weights(target_c, bg_penalty=bg_penalty,
                                           hi_boost=hi_boost, hi_threshold=hi_threshold,
                                           edge_sigma=edge_sigma, edge_boost=edge_boost)
    forbidden_c, _, _, _ = build_adaptive_corridors(target_c, border=border)

    grid_c = np.zeros((cH, cW), dtype=np.int8)
    avail_c = np.argwhere(forbidden_c == 0)
    idx_c = rng.choice(len(avail_c), size=min(int(density*cW*cH), len(avail_c)), replace=False)
    for i in idx_c: grid_c[avail_c[i][0], avail_c[i][1]] = 1

    t1 = time.perf_counter()
    grid_c, lc, hc = run_sa(sa_fn, grid_c, target_c, weights_c, forbidden_c,
                              n_iters=coarse_iters, T_start=T_coarse_start,
                              T_min=T_min, alpha=alpha_coarse, border=border, seed=seed)
    print(f"  Coarse done {time.perf_counter()-t1:.1f}s  loss={lc:.0f}  density={grid_c.mean():.3f}", flush=True)

    # ── Upsample ────────────────────────────────────────────────────────
    from PIL import Image as PILImage
    ci = PILImage.fromarray(grid_c.astype(np.uint8)*255)
    fi = ci.resize((board_w, board_h), PILImage.NEAREST)
    grid = (np.array(fi, dtype=np.uint8) > 127).astype(np.int8)
    grid[forbidden == 1] = 0

    # ── Step 4: fine SA ─────────────────────────────────────────────────
    print(f"[{label}] Fine SA ({fine_iters:,} iters)…", flush=True)
    t2 = time.perf_counter()
    grid, lf, hf = run_sa(sa_fn, grid, target, weights, forbidden,
                           n_iters=fine_iters, T_start=T_fine, T_min=T_min,
                           alpha=alpha_fine, border=border, seed=seed+1)
    grid[forbidden == 1] = 0
    print(f"  Fine done {time.perf_counter()-t2:.1f}s  loss={lf:.0f}  density={grid.mean():.3f}", flush=True)

    # ── Step 5: refine SA with underfill-augmented weights ───────────────
    print(f"[{label}] Refine SA ({refine_iters:,} iters)…", flush=True)
    N_cur    = compute_N(grid)
    underfill = np.clip(target - N_cur.astype(np.float32), 0.0, 8.0) / 8.0
    w_aug     = (weights * (1.0 + 1.5 * underfill)).astype(np.float32)

    t3 = time.perf_counter()
    grid, lr, hr = run_sa(sa_fn, grid, target, w_aug, forbidden,
                           n_iters=refine_iters, T_start=T_refine, T_min=T_min,
                           alpha=alpha_refine, border=border, seed=seed+2)
    grid[forbidden == 1] = 0
    print(f"  Refine done {time.perf_counter()-t3:.1f}s  loss={lr:.0f}  density={grid.mean():.3f}", flush=True)

    # ── Step 6: validate ────────────────────────────────────────────────
    assert_board_valid(grid, forbidden, label='post-SA')
    print("  assert_board_valid PASSED (post-SA)", flush=True)

    # ── Step 7: repair ──────────────────────────────────────────────────
    try:
        from .solver import solve_board
    except ImportError:
        from solver import solve_board
    sr_pre = solve_board(grid, max_rounds=50, mode='trial')
    repair_budget = max(60.0, sr_pre.n_unknown * 0.15 + 30.0)
    print(f"[{label}] Repair budget={repair_budget:.0f}s  n_unknown={sr_pre.n_unknown}…", flush=True)

    phase1_result = run_phase1_repair(
        grid, target, weights, forbidden,
        time_budget_s=min(repair_budget, 120.0), max_rounds=300,
        search_radius=6, verbose=verbose, checkpoint_dir=out_dir)
    grid = phase1_result.grid
    repair_reason = phase1_result.stop_reason
    grid[forbidden == 1] = 0

    # ── Step 8: validate post-repair ────────────────────────────────────
    assert_board_valid(grid, forbidden, label='post-repair')
    print("  assert_board_valid PASSED (post-repair)", flush=True)

    # ── Step 9: metrics ──────────────────────────────────────────────────
    try:
        from .solver import solve_board as _solve
    except ImportError:
        from solver import solve_board as _solve
    sr_final = _solve(grid, max_rounds=300, mode='full')
    N_final  = compute_N(grid)
    err      = np.abs(N_final.astype(np.float32) - target)
    total_time = time.perf_counter() - t_total

    metrics = {
        "label":          label,
        "board":          f"{board_w}x{board_h}",
        "cells":          board_w * board_h,
        "abs_error_variance": float(err.var()),
        "mean_abs_error": float(err.mean()),
        "pct_within_1":   float(np.mean(err <= 1.0) * 100),
        "pct_within_2":   float(np.mean(err <= 2.0) * 100),
        "hi_err":         float(err[target >= 3.0].mean()) if (target >= 3.0).any() else 0.0,
        "bg_err":         float(err[target <  1.0].mean()) if (target <  1.0).any() else 0.0,
        "mine_density":   float(grid.mean()),
        "corridor_pct":   float(corridor_pct),
        "coverage":       float(sr_final.coverage),
        "solvable":       bool(sr_final.solvable),
        "mine_accuracy":  float(sr_final.mine_accuracy),
        "n_unknown":      int(sr_final.n_unknown),
        "repair_reason":  repair_reason,
        "total_time_s":   float(total_time),
        "seed":           seed,
        # Iter 2 extra fields
        "bg_penalty":     bg_penalty,
        "hi_boost":       hi_boost,
        "hi_threshold":   hi_threshold,
        "iter":           iter_num,
    }

    print(f"\n{'='*55}", flush=True)
    print(f"  RESULTS [{label}] iter{iter_num}", flush=True)
    for k, v in metrics.items():
        print(f"    {k:22s}: {v}", flush=True)
    print(f"{'='*55}\n", flush=True)

    # ── Step 10: saves + report ──────────────────────────────────────────
    base     = f"iter{iter_num}_{label}"
    json_path = os.path.join(out_dir, f"metrics_{base}.json")
    npy_path  = os.path.join(out_dir, f"grid_{base}.npy")
    png_path  = os.path.join(out_dir, f"{base}_FINAL.png")

    atomic_save_json(metrics, json_path)
    atomic_save_npy(grid, npy_path)

    all_hist = np.concatenate([hc, hf, hr])
    render_report(target, grid, sr_final, all_hist,
                  title=f"Mine-Streaker Iter{iter_num} — {label}  "
                        f"[bg={bg_penalty} hi={hi_boost}]",
                  save_path=png_path, dpi=120)

    print(f"  Saved: {json_path}", flush=True)
    print(f"  Saved: {npy_path}",  flush=True)
    print(f"  Saved: {png_path}",  flush=True)
    return metrics
