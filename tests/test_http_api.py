from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.fixture_mapping import (
    FixtureQuantityRef,
    FixtureQuantitySourceKind,
    TemplateFixtureMappingRule,
)
from app.domain.item import Item
from app.domain.project import Project
from app.domain.stage import Stage
from app.domain.template import Template
from app.domain.user import User
from app.http.main import create_app
from app.http.security import hash_password
from app.infrastructure.sqlite_db import SqliteDb
from app.infrastructure.sqlite_item_repository import SqliteItemRepository
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository
from app.infrastructure.sqlite_takeoff_line_repository import SqliteTakeoffLineRepository
from app.infrastructure.sqlite_takeoff_repository import SqliteTakeoffRepository
from app.infrastructure.sqlite_template_fixture_mapping_repository import (
    SqliteTemplateFixtureMappingRepository,
)
from app.infrastructure.sqlite_template_repository import SqliteTemplateRepository
from app.infrastructure.sqlite_user_repository import SqliteUserRepository


def _build_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "http.db"
    conn = SqliteDb(path=db_path).connect()
    try:
        user_repo = SqliteUserRepository(conn=conn)
        user_repo.upsert(
            User(
                user_id="u-editor",
                username="editor",
                display_name="Editor User",
                role="editor",
                password_hash=hash_password("secret"),
            )
        )
        user_repo.upsert(
            User(
                user_id="u-viewer",
                username="viewer",
                display_name="Viewer User",
                role="viewer",
                password_hash=hash_password("secret"),
            )
        )

        template_repo = SqliteTemplateRepository(conn=conn)
        for code, name, category in (
            ("TH_STANDARD", "TH Standard", "TH"),
            ("VILLA_1331", "Villa 1331", "VILLAS"),
            ("VILLA_STANDARD", "Villa Standard", "VILLAS"),
            ("SF_GENERIC", "SF Generic", "SF"),
            ("TH_DEFAULT", "TH Default", "TH"),
        ):
            template_repo.upsert(Template(code=code, name=name, category=category))

        SqliteProjectRepository(conn=conn).upsert(
            Project(
                code="PROJ-001",
                name="Project One",
                contractor="Lennar",
                foreman="Jose",
            )
        )

        item_repo = SqliteItemRepository(conn=conn)
        item_repo.upsert(
            Item(
                code="TEST-ITEM",
                item_number=None,
                description="Test Fixture",
                details="Baseline",
                unit_price=Decimal("10.00"),
                taxable=True,
                category="Sewer Line Material",
            )
        )
        item_repo.upsert(
            Item(
                code="TEST-KITCH-1",
                item_number=None,
                description="Kitchen Faucet A",
                details="Variant A",
                unit_price=Decimal("20.00"),
                taxable=True,
                category="Kitchen Faucet",
            )
        )
        item_repo.upsert(
            Item(
                code="TEST-KITCH-2",
                item_number=None,
                description="Kitchen Faucet B",
                details="Variant B",
                unit_price=Decimal("21.00"),
                taxable=True,
                is_active=False,
                category="Kitchen Faucet",
            )
        )

        SqliteTemplateFixtureMappingRepository(conn=conn).upsert(
            TemplateFixtureMappingRule(
                mapping_id="map-ground",
                template_code="TH_STANDARD",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.PLAN,
                    source_name="sewer_distance_lf",
                ),
                item_code="TEST-ITEM",
                qty_multiplier=Decimal("1.0"),
                stage=Stage.GROUND,
                factor=Decimal("1.0"),
                sort_order=10,
            )
        )
    finally:
        conn.close()

    app = create_app(db_path=db_path, session_secret="test-secret")
    return TestClient(app)


def _login(client: TestClient, username: str, password: str = "secret") -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200


def test_auth_login_me_logout(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    login = client.post("/api/v1/auth/login", json={"username": "editor", "password": "secret"})
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "editor"

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["username"] == "editor"

    logout = client.post("/api/v1/auth/logout", json={})
    assert logout.status_code == 204

    me_after = client.get("/api/v1/auth/me")
    assert me_after.status_code == 401
    assert me_after.json()["error"]["code"] == "unauthorized"


def test_templates_endpoints_enforce_official_and_editor_admin_access(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    _login(client, "viewer")

    response = client.get("/api/v1/templates")
    assert response.status_code == 200
    codes = [row["template_code"] for row in response.json()["items"]]
    assert codes == ["TH_STANDARD", "VILLA_1331", "VILLA_STANDARD", "SF_GENERIC"]
    assert "TH_DEFAULT" not in codes

    admin = client.get("/api/v1/admin/templates")
    assert admin.status_code == 403
    assert admin.json()["error"]["code"] == "forbidden"

    client = _build_client(tmp_path)
    _login(client, "editor")
    admin = client.get("/api/v1/admin/templates")
    assert admin.status_code == 200
    admin_codes = [row["template_code"] for row in admin.json()["items"]]
    assert "TH_DEFAULT" in admin_codes


def test_items_endpoint_filters_by_category_and_excludes_inactive_by_default(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    _login(client, "viewer")

    response = client.get("/api/v1/items")
    assert response.status_code == 200
    all_codes = [row["code"] for row in response.json()["items"]]
    assert "TEST-ITEM" in all_codes
    assert "TEST-KITCH-1" in all_codes
    assert "TEST-KITCH-2" not in all_codes

    kitchen = client.get("/api/v1/items", params={"category": "Kitchen Faucet"})
    assert kitchen.status_code == 200
    rows = kitchen.json()["items"]
    assert [row["code"] for row in rows] == ["TEST-KITCH-1"]
    assert rows[0]["category"] == "Kitchen Faucet"


def test_generate_projects_list_and_current_takeoff_read_flow(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    _login(client, "editor")

    generate = client.post(
        "/api/v1/takeoffs/generate-from-plan",
        json={
            "project_code": "PROJ-001",
            "template_code": "TH_STANDARD",
            "tax_rate_override": None,
            "plan": {
                "stories": 1,
                "kitchens": 1,
                "garbage_disposals": 0,
                "laundry_rooms": 0,
                "lav_faucets": 0,
                "toilets": 0,
                "showers": 0,
                "bathtubs": 0,
                "half_baths": 0,
                "double_bowl_vanities": 0,
                "hose_bibbs": 0,
                "ice_makers": 0,
                "water_heater_tank_qty": 0,
                "water_heater_tankless_qty": 0,
                "sewer_distance_lf": "10",
                "water_distance_lf": "0"
            }
        },
    )
    assert generate.status_code == 201
    takeoff_id = generate.json()["takeoff"]["takeoff_id"]

    duplicate = client.post(
        "/api/v1/takeoffs/generate-from-plan",
        json={
            "project_code": "PROJ-001",
            "template_code": "TH_STANDARD",
            "tax_rate_override": None,
            "plan": {
                "stories": 1,
                "kitchens": 1,
                "garbage_disposals": 0,
                "laundry_rooms": 0,
                "lav_faucets": 0,
                "toilets": 0,
                "showers": 0,
                "bathtubs": 0,
                "half_baths": 0,
                "double_bowl_vanities": 0,
                "hose_bibbs": 0,
                "ice_makers": 0,
                "water_heater_tank_qty": 0,
                "water_heater_tankless_qty": 0,
                "sewer_distance_lf": "10",
                "water_distance_lf": "0"
            }
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "current_takeoff_exists"
    assert duplicate.json()["error"]["details"]["takeoff_id"] == takeoff_id

    projects = client.get("/api/v1/projects")
    assert projects.status_code == 200
    row = projects.json()["items"][0]
    assert row["project_code"] == "PROJ-001"
    assert "template_name" not in row["current_takeoffs"][0]

    current = client.get(f"/api/v1/takeoffs/{takeoff_id}")
    assert current.status_code == 200
    assert current.json()["takeoff"]["summary"]["stage_counts"] == {
        "ground": 1,
        "topout": 0,
        "final": 0,
    }

    lines = client.get(f"/api/v1/takeoffs/{takeoff_id}/lines")
    assert lines.status_code == 200
    assert len(lines.json()["items"]) == 1
    assert lines.json()["items"][0]["line_id"]


def test_line_patch_requires_payload_and_supports_line_id_updates(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    _login(client, "editor")

    generate = client.post(
        "/api/v1/takeoffs/generate-from-plan",
        json={
            "project_code": "PROJ-001",
            "template_code": "TH_STANDARD",
            "tax_rate_override": None,
            "plan": {
                "stories": 1,
                "kitchens": 1,
                "garbage_disposals": 0,
                "laundry_rooms": 0,
                "lav_faucets": 0,
                "toilets": 0,
                "showers": 0,
                "bathtubs": 0,
                "half_baths": 0,
                "double_bowl_vanities": 0,
                "hose_bibbs": 0,
                "ice_makers": 0,
                "water_heater_tank_qty": 0,
                "water_heater_tankless_qty": 0,
                "sewer_distance_lf": "10",
                "water_distance_lf": "0"
            }
        },
    )
    takeoff_id = generate.json()["takeoff"]["takeoff_id"]
    line_id = client.get(f"/api/v1/takeoffs/{takeoff_id}/lines").json()["items"][0]["line_id"]

    empty_patch = client.patch(f"/api/v1/takeoffs/{takeoff_id}/lines/{line_id}", json={})
    assert empty_patch.status_code == 422
    assert empty_patch.json()["error"]["code"] == "validation_error"

    patch = client.patch(
        f"/api/v1/takeoffs/{takeoff_id}/lines/{line_id}",
        json={"qty": "12.0"},
    )
    assert patch.status_code == 200
    assert patch.json()["line"]["qty"] == "12.0"


def test_viewer_cannot_mutate_lines(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    _login(client, "editor")

    generate = client.post(
        "/api/v1/takeoffs/generate-from-plan",
        json={
            "project_code": "PROJ-001",
            "template_code": "TH_STANDARD",
            "tax_rate_override": None,
            "plan": {
                "stories": 1,
                "kitchens": 1,
                "garbage_disposals": 0,
                "laundry_rooms": 0,
                "lav_faucets": 0,
                "toilets": 0,
                "showers": 0,
                "bathtubs": 0,
                "half_baths": 0,
                "double_bowl_vanities": 0,
                "hose_bibbs": 0,
                "ice_makers": 0,
                "water_heater_tank_qty": 0,
                "water_heater_tankless_qty": 0,
                "sewer_distance_lf": "10",
                "water_distance_lf": "0"
            }
        },
    )
    takeoff_id = generate.json()["takeoff"]["takeoff_id"]
    line_id = client.get(f"/api/v1/takeoffs/{takeoff_id}/lines").json()["items"][0]["line_id"]

    client = _build_client(tmp_path)
    _login(client, "viewer")

    patch = client.patch(
        f"/api/v1/takeoffs/{takeoff_id}/lines/{line_id}",
        json={"qty": "11.0"},
    )
    assert patch.status_code == 403
    assert patch.json()["error"]["code"] == "forbidden"

    delete = client.delete(f"/api/v1/takeoffs/{takeoff_id}/lines/{line_id}")
    assert delete.status_code == 403
    assert delete.json()["error"]["code"] == "forbidden"


def test_revision_endpoint_creates_version_and_then_conflicts_when_locked(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    _login(client, "editor")

    generate = client.post(
        "/api/v1/takeoffs/generate-from-plan",
        json={
            "project_code": "PROJ-001",
            "template_code": "TH_STANDARD",
            "tax_rate_override": None,
            "plan": {
                "stories": 1,
                "kitchens": 1,
                "garbage_disposals": 0,
                "laundry_rooms": 0,
                "lav_faucets": 0,
                "toilets": 0,
                "showers": 0,
                "bathtubs": 0,
                "half_baths": 0,
                "double_bowl_vanities": 0,
                "hose_bibbs": 0,
                "ice_makers": 0,
                "water_heater_tank_qty": 0,
                "water_heater_tankless_qty": 0,
                "sewer_distance_lf": "10",
                "water_distance_lf": "0"
            }
        },
    )
    takeoff_id = generate.json()["takeoff"]["takeoff_id"]

    revise = client.post(f"/api/v1/takeoffs/{takeoff_id}/revisions", json={})
    assert revise.status_code == 201
    version_id = revise.json()["version"]["version_id"]

    versions = client.get(f"/api/v1/takeoffs/{takeoff_id}/versions")
    assert versions.status_code == 200
    assert versions.json()["items"][0]["version_id"] == version_id

    version_detail = client.get(f"/api/v1/versions/{version_id}")
    assert version_detail.status_code == 200
    assert version_detail.json()["version"]["summary"]["line_count"] == 1

    locked = client.post(f"/api/v1/takeoffs/{takeoff_id}/revisions", json={})
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "takeoff_locked"
