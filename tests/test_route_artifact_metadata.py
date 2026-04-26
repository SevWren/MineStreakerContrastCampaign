import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from pipeline import RepairRouteResult, write_repair_route_artifacts


class RouteArtifactMetadataTests(unittest.TestCase):
    def test_route_artifacts_include_metadata_and_return_shape(self):
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            route = RepairRouteResult(
                grid=np.zeros((2, 2), dtype=np.int8),
                sr=object(),
                selected_route="phase2_full_repair",
                route_result="solved",
                failure_taxonomy={"dominant_failure_class": "sealed_single_mesa"},
                visual_delta_summary={"visual_delta": 0.0},
                decision={"selected_route": "phase2_full_repair", "route_result": "solved"},
            )
            metadata = {
                "run_id": "20260426T000000Z_line_art_irl_11_v2_300w_seed11",
                "generated_at_utc": "2026-04-26T00:00:00.000Z",
                "source_image_project_relative_path": "assets/line_art_irl_11_v2.png",
                "source_image_sha256": "abc123",
                "metrics_path": "results/iter9/test/metrics_iter9_300x370.json",
            }
            result = write_repair_route_artifacts(
                str(out_dir),
                "300x370",
                route,
                artifact_metadata=metadata,
            )

            self.assertEqual(
                set(result.keys()),
                {"failure_taxonomy", "repair_route_decision", "visual_delta_summary"},
            )
            for key in ("failure_taxonomy", "repair_route_decision", "visual_delta_summary"):
                path = Path(result[key])
                self.assertTrue(path.exists())
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("artifact_metadata", payload)
                self.assertEqual(payload["artifact_metadata"], metadata)


if __name__ == "__main__":
    unittest.main()
