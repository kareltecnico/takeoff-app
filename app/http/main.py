from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.application.authenticate_user import AuthenticateUser, AuthenticationError
from app.application.delete_takeoff_line import DeleteTakeoffLine
from app.application.errors import InvalidInputError
from app.application.generate_takeoff_from_plan_reading import GenerateTakeoffFromPlanReading
from app.application.inspect_takeoff import InspectTakeoff
from app.application.list_takeoff_lines import ListTakeoffLines
from app.application.projects import Projects
from app.application.update_takeoff_line import UpdateTakeoffLine
from app.domain.output_format import OutputFormat
from app.domain.plan_reading_input import PlanReadingInput
from app.domain.stage import Stage
from app.domain.totals import GrandTotals, TakeoffLineInput, calc_grand_totals
from app.domain.user import User
from app.http.dependencies import (
    OFFICIAL_TEMPLATE_CODES,
    RequestContext,
    get_authenticator,
    get_context,
    get_current_user,
    require_editor,
)
from app.http.errors import raise_api_error, translate_exception
from app.http.schemas import (
    ExportRequest,
    GenerateTakeoffRequest,
    LoginRequest,
    ProjectCreateRequest,
    UpdateLineRequest,
)
from app.infrastructure.renderer_registry import RendererRegistry
from app.application.render_takeoff_from_snapshot import (
    RenderTakeoffFromSnapshot,
    RenderTakeoffFromVersion,
)
from app.config import AppConfig


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def _decimal_str(value: Decimal) -> str:
    return str(value)


def _project_status(is_active: bool) -> str:
    return "open" if is_active else "closed"


def _is_official_template(template_code: str) -> bool:
    return template_code in OFFICIAL_TEMPLATE_CODES


def _totals_payload(grand_totals: GrandTotals) -> dict[str, str]:
    return {
        "subtotal": _money(grand_totals.subtotal),
        "tax": _money(grand_totals.tax),
        "total": _money(grand_totals.total_after_discount),
    }


def _line_to_payload(line: Any) -> dict[str, Any]:
    return {
        "line_id": getattr(line, "line_id", None),
        "mapping_id": getattr(line, "mapping_id", None),
        "item_code": line.item_code,
        "description": line.description_snapshot,
        "qty": _decimal_str(line.qty),
        "stage": (line.stage.value if isinstance(line.stage, Stage) else str(line.stage or "final")),
        "factor": _decimal_str(line.factor),
        "sort_order": int(line.sort_order),
    }


def _version_line_to_payload(line: Any) -> dict[str, Any]:
    return {
        "version_line_id": getattr(line, "version_line_id", None),
        "mapping_id": getattr(line, "mapping_id", None),
        "item_code": line.item_code,
        "description": line.description_snapshot,
        "qty": _decimal_str(line.qty),
        "stage": str(line.stage),
        "factor": _decimal_str(line.factor),
        "sort_order": int(line.sort_order),
    }


def _totals_from_version_lines(lines: tuple[Any, ...], tax_rate: Decimal, valve_discount: Decimal) -> GrandTotals:
    inputs = [
        TakeoffLineInput(
            stage=Stage(str(line.stage)),
            price=line.unit_price_snapshot,
            qty=line.qty,
            factor=line.factor,
            taxable=line.taxable_snapshot,
        )
        for line in lines
    ]
    return calc_grand_totals(inputs, valve_discount=valve_discount, tax_rate=tax_rate)


def _template_payload(template: Any) -> dict[str, Any]:
    return {
        "template_code": template.code,
        "template_name": template.name,
        "category": template.category,
    }


def _item_payload(item: Any) -> dict[str, Any]:
    return {
        "code": item.code,
        "item_number": item.item_number,
        "description": item.description,
        "details": item.details,
        "category": item.category,
        "unit_price": _money(item.unit_price),
        "taxable": item.taxable,
        "is_active": item.is_active,
    }


def _template_admin_payload(template: Any, *, mapping_count: int) -> dict[str, Any]:
    return {
        "template_code": template.code,
        "template_name": template.name,
        "category": template.category,
        "is_active": template.is_active,
        "is_official": _is_official_template(template.code),
        "is_legacy": not _is_official_template(template.code),
        "mapping_count": mapping_count,
    }


def _takeoff_timestamps(ctx: RequestContext, *, takeoff_id: str) -> tuple[str, str]:
    row = ctx.conn.execute(
        """
        SELECT created_at, updated_at
        FROM takeoffs
        WHERE takeoff_id = ?
        """,
        (takeoff_id,),
    ).fetchone()
    if row is None:
        raise InvalidInputError(f"Takeoff not found: {takeoff_id}")
    return str(row["created_at"]), str(row["updated_at"])


def create_app(*, db_path: Path, session_secret: str = "dev-session-secret") -> FastAPI:
    app = FastAPI(title="Take-Off App API", version="0.1.0")
    app.state.db_path = str(db_path)
    app.state.export_root = str(Path("outputs/http"))
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret,
        same_site="lax",
        https_only=False,
    )

    @app.exception_handler(InvalidInputError)
    async def handle_invalid_input(_: Request, exc: InvalidInputError) -> JSONResponse:
        http_exc = translate_exception(exc)
        return JSONResponse(status_code=http_exc.status_code, content=http_exc.detail)

    @app.exception_handler(AuthenticationError)
    async def handle_authentication_error(_: Request, exc: AuthenticationError) -> JSONResponse:
        http_exc = translate_exception(exc)
        return JSONResponse(status_code=http_exc.status_code, content=http_exc.detail)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        field_errors: dict[str, str] = {}
        for err in exc.errors():
            loc = [str(part) for part in err.get("loc", ()) if part != "body"]
            if not loc:
                continue
            field_errors[".".join(loc)] = str(err.get("msg", "Invalid value"))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "One or more fields are invalid.",
                    "details": {"field_errors": field_errors},
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"error": {"code": "bad_request", "message": str(exc.detail)}}
        return JSONResponse(status_code=exc.status_code, content=detail)

    @app.post("/api/v1/auth/login")
    def login(
        payload: LoginRequest,
        request: Request,
        auth: AuthenticateUser = Depends(get_authenticator),
    ) -> dict[str, Any]:
        user = auth(username=payload.username, password=payload.password)
        request.session.clear()
        request.session["user_id"] = user.user_id
        request.session["role"] = user.role
        return {
            "user": {
                "id": user.user_id,
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role,
            }
        }

    @app.post("/api/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(request: Request) -> Response:
        request.session.clear()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/api/v1/auth/me")
    def me(user: User = Depends(get_current_user)) -> dict[str, Any]:
        return {
            "user": {
                "id": user.user_id,
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role,
            }
        }

    @app.get("/api/v1/projects")
    def list_projects(
        q: str | None = None,
        status_filter: str | None = Query(default=None, alias="status"),
        _: User = Depends(get_current_user),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        projects = Projects(repo=ctx.projects).list(include_inactive=True)
        inspect_takeoff = InspectTakeoff(takeoff_repo=ctx.takeoffs, takeoff_line_repo=ctx.takeoff_lines)

        items: list[dict[str, Any]] = []
        for project in projects:
            project_status = _project_status(project.is_active)
            if status_filter is not None and project_status != status_filter:
                continue
            if q:
                haystack = " ".join(
                    filter(None, [project.code, project.name, project.contractor, project.foreman])
                ).lower()
                if q.lower() not in haystack:
                    continue

            current_takeoffs: list[dict[str, Any]] = []
            for takeoff in ctx.takeoffs.list_for_project(project.code):
                inspection = inspect_takeoff(takeoff_id=takeoff.takeoff_id)
                _, updated_at = _takeoff_timestamps(ctx, takeoff_id=takeoff.takeoff_id)
                current_takeoffs.append(
                    {
                        "takeoff_id": takeoff.takeoff_id,
                        "template_code": takeoff.template_code,
                        "updated_at": updated_at,
                        "totals": _totals_payload(inspection.grand_totals),
                        "is_locked": takeoff.is_locked,
                        "version_count": len(inspection.versions),
                    }
                )

            items.append(
                {
                    "project_code": project.code,
                    "project_name": project.name,
                    "contractor_name": project.contractor,
                    "foreman_name": project.foreman,
                    "status": project_status,
                    "current_takeoffs": current_takeoffs,
                }
            )

        return {"items": items}

    @app.post("/api/v1/projects", status_code=status.HTTP_201_CREATED)
    def create_project(
        payload: ProjectCreateRequest,
        _: User = Depends(require_editor),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        try:
            ctx.projects.get(payload.project_code)
        except InvalidInputError:
            pass
        else:
            raise_api_error(
                status_code=status.HTTP_409_CONFLICT,
                code="validation_error",
                message=f"Project already exists: {payload.project_code}",
            )

        Projects(repo=ctx.projects).add(
            code=payload.project_code,
            name=payload.project_name,
            contractor=payload.contractor_name,
            foreman=payload.foreman_name,
        )
        project = ctx.projects.get(payload.project_code)
        return {
            "project": {
                "project_code": project.code,
                "project_name": project.name,
                "contractor_name": project.contractor,
                "foreman_name": project.foreman,
                "status": _project_status(project.is_active),
            }
        }

    @app.get("/api/v1/projects/{project_code}")
    def get_project(
        project_code: str,
        _: User = Depends(get_current_user),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        project = ctx.projects.get(project_code)
        return {
            "project": {
                "project_code": project.code,
                "project_name": project.name,
                "contractor_name": project.contractor,
                "foreman_name": project.foreman,
                "status": _project_status(project.is_active),
            }
        }

    @app.get("/api/v1/templates")
    def list_templates(
        _: User = Depends(get_current_user),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        templates = [
            template
            for template in ctx.templates.list(include_inactive=False)
            if template.code in OFFICIAL_TEMPLATE_CODES
        ]
        templates.sort(key=lambda template: OFFICIAL_TEMPLATE_CODES.index(template.code))
        return {"items": [_template_payload(template) for template in templates]}

    @app.get("/api/v1/items")
    def list_items(
        category: str | None = None,
        _: User = Depends(get_current_user),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        items = list(ctx.items.list(include_inactive=False))
        if category is not None:
            items = [item for item in items if item.category == category]
        items.sort(key=lambda item: (item.category or "", item.code))
        return {"items": [_item_payload(item) for item in items]}

    @app.get("/api/v1/admin/templates")
    def list_admin_templates(
        _: User = Depends(require_editor),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        templates = ctx.templates.list(include_inactive=True)
        items = []
        for template in templates:
            mapping_count = len(ctx.template_mappings.list_for_template(template.code))
            items.append(_template_admin_payload(template, mapping_count=mapping_count))
        return {"items": items}

    @app.get("/api/v1/templates/{template_code}")
    def get_template(
        template_code: str,
        user: User = Depends(get_current_user),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        template = ctx.templates.get(template_code)
        if not _is_official_template(template.code) and user.role != "editor":
            raise_api_error(
                status_code=status.HTTP_404_NOT_FOUND,
                code="not_found",
                message=f"Template not found: {template_code}",
            )
        mapping_count = len(ctx.template_mappings.list_for_template(template.code))
        return {"template": _template_admin_payload(template, mapping_count=mapping_count)}

    @app.post("/api/v1/takeoffs/generate-from-plan", status_code=status.HTTP_201_CREATED)
    def generate_takeoff(
        payload: GenerateTakeoffRequest,
        _: User = Depends(require_editor),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        takeoff_id = GenerateTakeoffFromPlanReading(
            project_repo=ctx.projects,
            template_repo=ctx.templates,
            template_fixture_mapping_repo=ctx.template_mappings,
            project_fixture_override_repo=ctx.project_overrides,
            item_repo=ctx.items,
            takeoff_repo=ctx.takeoffs,
            takeoff_line_repo=ctx.takeoff_lines,
        )(
            project_code=payload.project_code,
            template_code=payload.template_code,
            plan=PlanReadingInput(**payload.plan.model_dump()),
            tax_rate_override=payload.tax_rate_override,
        )
        takeoff = ctx.takeoffs.get(takeoff_id)
        created_at, updated_at = _takeoff_timestamps(ctx, takeoff_id=takeoff_id)
        return {
            "takeoff": {
                "takeoff_id": takeoff.takeoff_id,
                "project_code": takeoff.project_code,
                "template_code": takeoff.template_code,
                "is_locked": takeoff.is_locked,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        }

    @app.get("/api/v1/takeoffs/{takeoff_id}")
    def get_takeoff(
        takeoff_id: str,
        _: User = Depends(get_current_user),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        inspection = InspectTakeoff(takeoff_repo=ctx.takeoffs, takeoff_line_repo=ctx.takeoff_lines)(
            takeoff_id=takeoff_id
        )
        project = ctx.projects.get(inspection.project_code)
        created_at, updated_at = _takeoff_timestamps(ctx, takeoff_id=takeoff_id)
        lines = ctx.takeoff_lines.list_for_takeoff(takeoff_id)
        return {
            "takeoff": {
                "takeoff_id": inspection.takeoff_id,
                "project": {
                    "project_code": project.code,
                    "project_name": project.name,
                    "status": _project_status(project.is_active),
                },
                "state": {
                    "is_current": True,
                    "is_locked": inspection.locked,
                },
                "created_at": created_at,
                "updated_at": updated_at,
                "totals": _totals_payload(inspection.grand_totals),
                "summary": {
                    "line_count": inspection.line_count,
                    "stage_counts": {
                        "ground": sum(1 for line in lines if line.stage == Stage.GROUND),
                        "topout": sum(1 for line in lines if line.stage == Stage.TOPOUT),
                        "final": sum(1 for line in lines if line.stage == Stage.FINAL),
                    },
                },
            }
        }

    @app.get("/api/v1/takeoffs/{takeoff_id}/lines")
    def get_takeoff_lines(
        takeoff_id: str,
        _: User = Depends(get_current_user),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        lines = ListTakeoffLines(repo=ctx.takeoff_lines)(takeoff_id=takeoff_id)
        return {"items": [_line_to_payload(line) for line in lines]}

    @app.patch("/api/v1/takeoffs/{takeoff_id}/lines/{line_id}")
    def update_takeoff_line(
        takeoff_id: str,
        line_id: str,
        payload: UpdateLineRequest,
        _: User = Depends(require_editor),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        if (
            payload.qty is None
            and payload.stage is None
            and payload.factor is None
            and payload.sort_order is None
        ):
            raise_api_error(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="validation_error",
                message="At least one of qty, stage, factor, sort_order must be provided",
            )

        stage_value = None
        if payload.stage is not None:
            try:
                stage_value = Stage(payload.stage)
            except ValueError:
                raise_api_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    code="validation_error",
                    message=f"Invalid stage: {payload.stage}",
                )

        UpdateTakeoffLine(repo=ctx.takeoff_lines)(
            takeoff_id=takeoff_id,
            line_id=line_id,
            qty=payload.qty,
            stage=stage_value,
            factor=payload.factor,
            sort_order=payload.sort_order,
        )

        lines = ctx.takeoff_lines.list_for_takeoff(takeoff_id)
        updated_line = next((line for line in lines if line.line_id == line_id), None)
        if updated_line is None:
            raise_api_error(
                status_code=status.HTTP_404_NOT_FOUND,
                code="line_not_found",
                message=f"Takeoff line not found: line_id={line_id}",
            )
        inspection = InspectTakeoff(takeoff_repo=ctx.takeoffs, takeoff_line_repo=ctx.takeoff_lines)(
            takeoff_id=takeoff_id
        )
        return {
            "line": _line_to_payload(updated_line),
            "totals": _totals_payload(inspection.grand_totals),
        }

    @app.delete("/api/v1/takeoffs/{takeoff_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_takeoff_line(
        takeoff_id: str,
        line_id: str,
        _: User = Depends(require_editor),
        ctx: RequestContext = Depends(get_context),
    ) -> Response:
        DeleteTakeoffLine(repo=ctx.takeoff_lines)(
            takeoff_id=takeoff_id,
            line_id=line_id,
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/v1/takeoffs/{takeoff_id}/revisions", status_code=status.HTTP_201_CREATED)
    def create_revision(
        takeoff_id: str,
        user: User = Depends(require_editor),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        takeoff = ctx.takeoffs.get(takeoff_id)
        project = ctx.projects.get(takeoff.project_code)
        if takeoff.is_locked:
            raise_api_error(
                status_code=status.HTTP_409_CONFLICT,
                code="takeoff_locked",
                message=f"Takeoff is locked: {takeoff_id}",
            )
        if not project.is_active:
            raise_api_error(
                status_code=status.HTTP_409_CONFLICT,
                code="project_closed",
                message=f"Project is closed; current takeoff cannot be edited: {takeoff_id}",
            )

        version_id = ctx.takeoffs.create_snapshot_version(
            takeoff_id=takeoff_id,
            created_by=user.username,
        )
        ctx.takeoffs.lock(takeoff_id=takeoff_id)
        version = ctx.takeoffs.get_version(version_id=version_id)
        return {
            "version": {
                "version_id": version.version_id,
                "takeoff_id": version.takeoff_id,
                "version_number": version.version_number,
                "created_at": version.created_at,
            }
        }

    @app.get("/api/v1/takeoffs/{takeoff_id}/versions")
    def list_versions(
        takeoff_id: str,
        _: User = Depends(get_current_user),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        versions = ctx.takeoffs.list_versions(takeoff_id=takeoff_id)
        items = []
        for version in versions:
            lines = ctx.takeoffs.list_version_lines(version_id=version.version_id)
            totals = _totals_from_version_lines(
                lines,
                tax_rate=version.tax_rate_snapshot,
                valve_discount=version.valve_discount_snapshot,
            )
            items.append(
                {
                    "version_id": version.version_id,
                    "version_number": version.version_number,
                    "created_at": version.created_at,
                    "totals": _totals_payload(totals),
                }
            )
        return {"items": items}

    @app.get("/api/v1/versions/{version_id}")
    def get_version(
        version_id: str,
        _: User = Depends(get_current_user),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        version = ctx.takeoffs.get_version(version_id=version_id)
        lines = ctx.takeoffs.list_version_lines(version_id=version_id)
        totals = _totals_from_version_lines(
            lines,
            tax_rate=version.tax_rate_snapshot,
            valve_discount=version.valve_discount_snapshot,
        )
        stage_counts = {
            "ground": sum(1 for line in lines if str(line.stage) == "ground"),
            "topout": sum(1 for line in lines if str(line.stage) == "topout"),
            "final": sum(1 for line in lines if str(line.stage) == "final"),
        }
        return {
            "version": {
                "version_id": version.version_id,
                "takeoff_id": version.takeoff_id,
                "version_number": version.version_number,
                "created_at": version.created_at,
                "totals": _totals_payload(totals),
                "summary": {
                    "line_count": len(lines),
                    "stage_counts": stage_counts,
                },
                "lines": [_version_line_to_payload(line) for line in lines],
            }
        }

    @app.post("/api/v1/takeoffs/{takeoff_id}/exports", status_code=status.HTTP_201_CREATED)
    def export_takeoff(
        takeoff_id: str,
        payload: ExportRequest,
        _: User = Depends(get_current_user),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        try:
            fmt = OutputFormat(payload.format)
        except ValueError:
            raise_api_error(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="validation_error",
                message=f"Invalid format: {payload.format}",
            )
        out_dir = Path(app.state.export_root)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"takeoff_{takeoff_id}.{fmt.value}"
        rendered = RenderTakeoffFromSnapshot(
            project_repo=ctx.projects,
            template_repo=ctx.templates,
            takeoff_repo=ctx.takeoffs,
            takeoff_line_repo=ctx.takeoff_lines,
            renderer_factory=RendererRegistry(),
            config=AppConfig(export_root=out_dir),
        )(takeoff_id=takeoff_id, out=out, fmt=fmt)
        return {
            "export": {
                "format": fmt.value,
                "file_name": rendered.name,
                "download_url": str(rendered),
            }
        }

    @app.post("/api/v1/versions/{version_id}/exports", status_code=status.HTTP_201_CREATED)
    def export_version(
        version_id: str,
        payload: ExportRequest,
        _: User = Depends(get_current_user),
        ctx: RequestContext = Depends(get_context),
    ) -> dict[str, Any]:
        try:
            fmt = OutputFormat(payload.format)
        except ValueError:
            raise_api_error(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="validation_error",
                message=f"Invalid format: {payload.format}",
            )
        out_dir = Path(app.state.export_root)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"version_{version_id}.{fmt.value}"
        rendered = RenderTakeoffFromVersion(
            project_repo=ctx.projects,
            template_repo=ctx.templates,
            takeoff_repo=ctx.takeoffs,
            renderer_factory=RendererRegistry(),
            config=AppConfig(export_root=out_dir),
        )(version_id=version_id, out=out, fmt=fmt)
        return {
            "export": {
                "format": fmt.value,
                "file_name": rendered.name,
                "download_url": str(rendered),
            }
        }

    return app
