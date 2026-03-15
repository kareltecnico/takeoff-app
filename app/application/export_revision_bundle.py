from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.application.generate_revision_report import GenerateRevisionReport
from app.application.render_takeoff_from_snapshot import RenderTakeoffFromVersion
from app.domain.output_format import OutputFormat
from app.infrastructure.renderer_registry import RendererRegistry

from decimal import Decimal
from app.domain.stage import Stage
from app.domain.totals import TakeoffLineInput, calc_stage_totals, calc_grand_totals


@dataclass
class ExportRevisionBundle:
    takeoff_repo: any
    project_repo: any
    template_repo: any
    config: any

    def __call__(self, *, version_id: str, out_dir: Path | None = None) -> Path:
        """
        Export a revision bundle containing:
        - rendered PDF
        - revision report
        - metadata.json
        """

        # Resolve output directory from config if not provided
        if out_dir is None:
            out_dir = getattr(self.config, "export_root", Path("outputs"))

        version = self.takeoff_repo.get_version(version_id=version_id)
        takeoff = self.takeoff_repo.get(takeoff_id=version.takeoff_id)

        project = self.project_repo.get(code=takeoff.project_code)
        template = self.template_repo.get(code=takeoff.template_code)

        version_number = version.version_number

        bundle_dir = (
            out_dir
            / project.code
            / template.code
            / f"v{version_number}"
        )

        bundle_dir.mkdir(parents=True, exist_ok=True)

        # -----------------------------
        # 1. Render Takeoff PDF
        # -----------------------------

        pdf_path = bundle_dir / f"takeoff_v{version_number}.pdf"

        RenderTakeoffFromVersion(
            project_repo=self.project_repo,
            template_repo=self.template_repo,
            takeoff_repo=self.takeoff_repo,
            renderer_factory=RendererRegistry(),
            config=self.config,
        )(
            version_id=version_id,
            out=pdf_path,
            fmt=OutputFormat.PDF,
        )

        # -----------------------------
        # 2. Revision report
        # -----------------------------

        previous_versions = self.takeoff_repo.list_versions(
            takeoff_id=version.takeoff_id
        )

        if len(previous_versions) >= 2:
            previous = previous_versions[1]

            report = GenerateRevisionReport(
                takeoff_repo=self.takeoff_repo
            )(
                version_a=previous.version_id,
                version_b=version.version_id,
            )

            report_path = bundle_dir / (
                f"revision_report_v{previous.version_number}_to_v{version_number}.txt"
            )

            report_path.write_text(report.to_text(), encoding="utf-8")

        # -----------------------------
        # 3. Metadata
        # -----------------------------

        metadata = {
            "version_id": version.version_id,
            "takeoff_id": version.takeoff_id,
            "project_code": project.code,
            "template_code": template.code,
            "version_number": version.version_number,
            "created_at": str(version.created_at),
            "created_by": version.created_by,
            "reason": version.reason,
            "integrity_hash": getattr(version, "integrity_hash", None),
            "integrity_schema_version": getattr(version, "integrity_schema_version", None),
            "generated_at": datetime.utcnow().isoformat(),
        }

        metadata_path = bundle_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        # -----------------------------
        # 3.5 Phase summary
        # -----------------------------

        try:
            version_lines = self.takeoff_repo.list_version_lines(version_id=version_id)

            inputs = []

            for ln in version_lines:
                stage = getattr(ln, "stage", None) or Stage.FINAL
                factor = getattr(ln, "factor", None) or Decimal("1.0")

                inputs.append(
                    TakeoffLineInput(
                        stage=stage,
                        price=ln.unit_price_snapshot,
                        qty=ln.qty,
                        factor=factor,
                        taxable=ln.taxable_snapshot,
                    )
                )

            ground = calc_stage_totals(inputs, stage=Stage.GROUND, tax_rate=version.tax_rate_snapshot)
            topout = calc_stage_totals(inputs, stage=Stage.TOPOUT, tax_rate=version.tax_rate_snapshot)
            final = calc_stage_totals(inputs, stage=Stage.FINAL, tax_rate=version.tax_rate_snapshot)

            grand = calc_grand_totals(
                inputs,
                valve_discount=version.valve_discount_snapshot,
                tax_rate=version.tax_rate_snapshot,
            )

            summary_text = f"""
GROUND
subtotal: {ground.subtotal:.2f}
tax: {ground.tax:.2f}
total: {ground.total:.2f}

TOPOUT
subtotal: {topout.subtotal:.2f}
tax: {topout.tax:.2f}
total: {topout.total:.2f}

FINAL
subtotal: {final.subtotal:.2f}
tax: {final.tax:.2f}
total: {final.total:.2f}

GRAND
subtotal: {grand.subtotal:.2f}
tax: {grand.tax:.2f}
total: {grand.total:.2f}
valve_discount: {grand.valve_discount:.2f}
after_discount: {grand.total_after_discount:.2f}
""".strip()

            phase_summary_path = bundle_dir / "phase_summary.txt"
            phase_summary_path.write_text(summary_text, encoding="utf-8")

        except Exception as e:
            print(f"WARNING: phase summary generation failed: {e}")

        # -----------------------------
        # 4. Optional mirror export
        # -----------------------------

        mirror_root = getattr(self.config, "mirror_export_root", None)

        if mirror_root:
            try:
                mirror_dir = (
                    Path(mirror_root)
                    / project.code
                    / template.code
                    / f"v{version_number}"
                )

                mirror_dir.mkdir(parents=True, exist_ok=True)

                for file in bundle_dir.iterdir():
                    target = mirror_dir / file.name
                    target.write_bytes(file.read_bytes())

                print(f"MIRROR export completed at: {mirror_dir}")

            except Exception as e:
                # Mirror failures should never break the main export
                print(f"WARNING: mirror export failed: {e}")

        return bundle_dir