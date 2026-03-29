# HTTP API MVP Specification — Take-Off App

## 1. Purpose

This document freezes the MVP HTTP/API contract used to bridge the existing Python backend to the approved frontend MVP.

It is intentionally:

- minimal
- stable
- role-aware
- aligned with validated backend behavior
- limited to the MVP workflow

This document does not define implementation details. It defines the JSON contract and expected behavior that the frontend and HTTP bridge must share.

---

## 2. MVP Role Model

The API supports exactly two roles:

- `editor`
- `viewer`

No additional role names are part of the MVP contract.

### Editor

Can:

- create projects
- generate CURRENT takeoffs
- inspect CURRENT takeoffs
- update/delete CURRENT lines
- create revisions/snapshots
- export/render
- access editor-only template admin endpoints

### Viewer

Can:

- inspect projects
- inspect CURRENT takeoffs
- inspect revision history
- inspect version detail
- export/view outputs if enabled

Cannot:

- create project
- generate takeoff
- update/delete lines
- create revisions
- access editor-only template admin endpoints

---

## 3. Authentication / Session

### Session Model

MVP uses simple login with cookie-based session auth.

### Endpoints

#### `POST /api/v1/auth/login`

Request:

```json
{
  "username": "editor1",
  "password": "secret"
}
```

Response `200`:

```json
{
  "user": {
    "id": "u_editor1",
    "username": "editor1",
    "display_name": "Editor 1",
    "role": "editor"
  }
}
```

#### `POST /api/v1/auth/logout`

Request:

```json
{}
```

Response:

- `204 No Content`

#### `GET /api/v1/auth/me`

Response `200`:

```json
{
  "user": {
    "id": "u_editor1",
    "username": "editor1",
    "display_name": "Editor 1",
    "role": "editor"
  }
}
```

### Access Rules

- unauthenticated requests return `401`
- authenticated but forbidden requests return `403`
- password reset remains operational/admin-only and outside MVP UI/API flow

---

## 4. MVP Endpoints

### Auth / Session

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Projects

- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{projectCode}`

### Templates

- `GET /api/v1/templates`
- `GET /api/v1/templates/{templateCode}`
- `GET /api/v1/admin/templates`

### Takeoffs

- `POST /api/v1/takeoffs/generate-from-plan`
- `GET /api/v1/takeoffs/{takeoffId}`
- `GET /api/v1/takeoffs/{takeoffId}/lines`
- `PATCH /api/v1/takeoffs/{takeoffId}/lines/{lineId}`
- `DELETE /api/v1/takeoffs/{takeoffId}/lines/{lineId}`
- `POST /api/v1/takeoffs/{takeoffId}/revisions`

### Versions

- `GET /api/v1/takeoffs/{takeoffId}/versions`
- `GET /api/v1/versions/{versionId}`

### Items

- `GET /api/v1/items`

### Exports

- `POST /api/v1/takeoffs/{takeoffId}/exports`
- `POST /api/v1/versions/{versionId}/exports`

Export behavior is intentionally minimal in MVP. This contract does not define export history or export admin workflows.

Current implementation caveat:

- export responses may still return a server-local file path string in `download_url` until a dedicated browser download endpoint is added

---

## 5. Templates Contract

### `GET /api/v1/templates`

Default behavior:

- returns only validated official templates used in the normal frontend creation flow

Expected set:

- `TH_STANDARD`
- `VILLA_1331`
- `VILLA_STANDARD`
- `SF_GENERIC`

Response `200`:

```json
{
  "items": [
    {
      "template_code": "TH_STANDARD",
      "template_name": "TH Standard",
      "category": "TH"
    },
    {
      "template_code": "VILLA_STANDARD",
      "template_name": "Villa Standard",
      "category": "VILLAS"
    }
  ]
}
```

### `GET /api/v1/admin/templates`

Editor-only endpoint for broader template visibility.

This endpoint may include:

- official templates
- legacy/provisional templates
- extra metadata useful for minimal template admin views

Viewer access must return `403`.

### `GET /api/v1/templates/{templateCode}`

Response `200`:

```json
{
  "template": {
    "template_code": "TH_STANDARD",
    "template_name": "TH Standard",
    "category": "TH",
    "is_active": true,
    "is_official": true,
    "is_legacy": false,
    "mapping_count": 30
  }
}
```

---

## 5.1 Items Contract

### `GET /api/v1/items`

Authenticated endpoint.

Default behavior:

- returns active catalog items only
- supports optional exact `category` filtering
- keeps the response minimal for Create / Generate selector use

Query params:

- `category` optional exact category name, for example `Kitchen Faucet`

Response `200`:

```json
{
  "items": [
    {
      "code": "XPLBFMKF0032",
      "item_number": "XPLBFMKF0032",
      "description": "FAUCET,KITCH,METHOD,CHROME",
      "details": "MOEN-7585-C CHROME",
      "category": "Kitchen Faucet",
      "unit_price": "145.06",
      "taxable": true,
      "is_active": true
    }
  ]
}
```

Current MVP use:

- drives category-aware item selectors on the Create / Generate page
- does not yet make selected items change backend generation behavior

---

## 6. Projects Contract

### `GET /api/v1/projects`

Query params:

- `q` optional search text
- `status` optional: `open|closed`

The response must stay minimal and practical for the MVP UI.

Do not include unnecessary template metadata in normal project list rows.

Response `200`:

```json
{
  "items": [
    {
      "project_code": "PROJ-001",
      "project_name": "Rancho Grande",
      "contractor_name": "Lennar",
      "foreman_name": "Jose",
      "status": "open",
      "current_takeoffs": [
        {
          "takeoff_id": "t_123",
          "template_code": "SF_GENERIC",
          "updated_at": "2026-03-24T10:15:00Z",
          "totals": {
            "subtotal": "6582.48",
            "tax": "156.91",
            "total": "6739.39"
          },
          "is_locked": false,
          "version_count": 2
        }
      ]
    }
  ]
}
```

### `POST /api/v1/projects`

Editor-only.

Request:

```json
{
  "project_code": "PROJ-010",
  "project_name": "New Community",
  "contractor_name": "Lennar",
  "foreman_name": "Carlos"
}
```

Response `201`:

```json
{
  "project": {
    "project_code": "PROJ-010",
    "project_name": "New Community",
    "contractor_name": "Lennar",
    "foreman_name": "Carlos",
    "status": "open"
  }
}
```

### `GET /api/v1/projects/{projectCode}`

Response `200`:

```json
{
  "project": {
    "project_code": "PROJ-001",
    "project_name": "Rancho Grande",
    "contractor_name": "Lennar",
    "foreman_name": "Jose",
    "status": "open"
  }
}
```

---

## 7. Takeoff Generation Contract

### `POST /api/v1/takeoffs/generate-from-plan`

Editor-only.

Request:

```json
{
  "project_code": "PROJ-001",
  "template_code": "SF_GENERIC",
  "tax_rate_override": null,
  "plan": {
    "stories": 2,
    "kitchens": 1,
    "garbage_disposals": 1,
    "laundry_rooms": 1,
    "lav_faucets": 3,
    "toilets": 3,
    "showers": 1,
    "bathtubs": 1,
    "half_baths": 1,
    "double_bowl_vanities": 0,
    "hose_bibbs": 2,
    "ice_makers": 0,
    "water_heater_tank_qty": 1,
    "water_heater_tankless_qty": 0,
    "sewer_distance_lf": 40,
    "water_distance_lf": 40
  }
}
```

Response `201`:

```json
{
  "takeoff": {
    "takeoff_id": "t_123",
    "project_code": "PROJ-001",
    "template_code": "SF_GENERIC",
    "is_locked": false,
    "created_at": "2026-03-24T10:00:00Z",
    "updated_at": "2026-03-24T10:00:00Z"
  }
}
```

### Existing CURRENT Takeoff Conflict

If a CURRENT takeoff already exists for the same `(project_code, template_code)`:

- do not overwrite
- do not regenerate silently
- return `409 current_takeoff_exists`
- include the existing `takeoff_id`

Response `409`:

```json
{
  "error": {
    "code": "current_takeoff_exists",
    "message": "A CURRENT takeoff already exists for project=PROJ-001 template=SF_GENERIC.",
    "details": {
      "project_code": "PROJ-001",
      "template_code": "SF_GENERIC",
      "takeoff_id": "t_existing"
    }
  }
}
```

---

## 8. Current Takeoff Contract

### `GET /api/v1/takeoffs/{takeoffId}`

Response `200`:

```json
{
  "takeoff": {
    "takeoff_id": "t_123",
    "project": {
      "project_code": "PROJ-001",
      "project_name": "Rancho Grande",
      "status": "open"
    },
    "state": {
      "is_current": true,
      "is_locked": false
    },
    "created_at": "2026-03-24T10:00:00Z",
    "updated_at": "2026-03-24T10:15:00Z",
    "totals": {
      "subtotal": "6582.48",
      "tax": "156.91",
      "total": "6739.39"
    },
    "summary": {
      "line_count": 22,
      "stage_counts": {
        "ground": 6,
        "topout": 5,
        "final": 11
      }
    }
  }
}
```

### `GET /api/v1/takeoffs/{takeoffId}/lines`

Response `200`:

```json
{
  "items": [
    {
      "line_id": "ln_001",
      "mapping_id": "sfg_ground_fixture_material",
      "item_code": "FW50M90110",
      "description": "MATL PER FIXTURE 2+ STORIES",
      "qty": "10.0",
      "stage": "ground",
      "factor": "0.30",
      "sort_order": 10
    }
  ]
}
```

The frontend groups the flat line list by stage.

---

## 9. Current Line Mutation Contract

### `PATCH /api/v1/takeoffs/{takeoffId}/lines/{lineId}`

Editor-only.

Allowed fields:

- `qty`
- `stage`
- `factor`
- `sort_order`

Request:

```json
{
  "qty": "12.0",
  "stage": "ground"
}
```

Response `200`:

```json
{
  "line": {
    "line_id": "ln_001",
    "mapping_id": "sfg_ground_fixture_material",
    "item_code": "FW50M90110",
    "description": "MATL PER FIXTURE 2+ STORIES",
    "qty": "12.0",
    "stage": "ground",
    "factor": "0.30",
    "sort_order": 10
  },
  "totals": {
    "subtotal": "6700.00",
    "tax": "160.00",
    "total": "6860.00"
  }
}
```

Validation rule:

- empty payload must return `422 validation_error`

### `DELETE /api/v1/takeoffs/{takeoffId}/lines/{lineId}`

Editor-only.

Response:

- `204 No Content`

Business-state conflicts return `409`, for example:

- takeoff locked
- project closed
- invalid mutable state

---

## 10. Revision Contract

### `POST /api/v1/takeoffs/{takeoffId}/revisions`

Editor-only.

This endpoint is allowed only for valid CURRENT/open takeoffs.

Allowed business state:

- CURRENT takeoff
- not locked
- project open

Blocked business states return `409`, including:

- `takeoff_locked`
- `project_closed`
- `invalid_takeoff_state`

Request:

```json
{}
```

Response `201`:

```json
{
  "version": {
    "version_id": "v_003",
    "takeoff_id": "t_123",
    "version_number": 3,
    "created_at": "2026-03-24T11:00:00Z"
  }
}
```

### `GET /api/v1/takeoffs/{takeoffId}/versions`

Response `200`:

```json
{
  "items": [
    {
      "version_id": "v_001",
      "version_number": 1,
      "created_at": "2026-03-20T14:00:00Z",
      "totals": {
        "subtotal": "6400.00",
        "tax": "150.00",
        "total": "6550.00"
      }
    }
  ]
}
```

### `GET /api/v1/versions/{versionId}`

Response `200`:

```json
{
  "version": {
    "version_id": "v_003",
    "takeoff_id": "t_123",
    "version_number": 3,
    "created_at": "2026-03-24T11:00:00Z",
    "totals": {
      "subtotal": "6700.00",
      "tax": "160.00",
      "total": "6860.00"
    },
    "summary": {
      "line_count": 22,
      "stage_counts": {
        "ground": 6,
        "topout": 5,
        "final": 11
      }
    },
    "lines": [
      {
        "version_line_id": "vl_001",
        "mapping_id": "sfg_ground_fixture_material",
        "item_code": "FW50M90110",
        "description": "MATL PER FIXTURE 2+ STORIES",
        "qty": "10.0",
        "stage": "ground",
        "factor": "0.30",
        "sort_order": 10
      }
    ]
  }
}
```

---

## 11. Export Contract

### `POST /api/v1/takeoffs/{takeoffId}/exports`

Request:

```json
{
  "format": "pdf"
}
```

Response `201`:

```json
{
  "export": {
    "format": "pdf",
    "file_name": "takeoff_t_123.pdf",
    "download_url": "/api/v1/downloads/exp_001"
  }
}
```

### `POST /api/v1/versions/{versionId}/exports`

Request:

```json
{
  "format": "pdf"
}
```

Response `201`:

```json
{
  "export": {
    "format": "pdf",
    "file_name": "takeoff_v3.pdf",
    "download_url": "/api/v1/downloads/exp_002"
  }
}
```

This export contract is intentionally minimal.

It does not include:

- export history
- export queue management
- admin export workflows

---

## 12. Error Contract

All non-2xx responses must use the same envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "One or more fields are invalid.",
    "details": {}
  }
}
```

### Expected Status Usage

- `400` malformed JSON or bad request envelope
- `401` unauthenticated
- `403` forbidden by role
- `404` resource not found
- `409` business-state conflict
- `422` field validation error

### Required Stable Error Codes

- `invalid_credentials`
- `unauthorized`
- `forbidden`
- `validation_error`
- `not_found`
- `current_takeoff_exists`
- `project_closed`
- `takeoff_locked`
- `invalid_takeoff_state`
- `no_resolved_lines`
- `line_not_found`

The frontend should rely on:

- HTTP status
- `error.code`
- `error.message`

---

## 13. Endpoints Required Before Frontend Coding Can Begin

Minimum required to start the first usable frontend slice:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/templates`
- `POST /api/v1/takeoffs/generate-from-plan`
- `GET /api/v1/takeoffs/{takeoffId}`
- `GET /api/v1/takeoffs/{takeoffId}/lines`
- `PATCH /api/v1/takeoffs/{takeoffId}/lines/{lineId}`
- `DELETE /api/v1/takeoffs/{takeoffId}/lines/{lineId}`
- `POST /api/v1/takeoffs/{takeoffId}/revisions`
- `GET /api/v1/takeoffs/{takeoffId}/versions`
- `GET /api/v1/versions/{versionId}`

---

## 14. Endpoints That Can Be Deferred Slightly

These can be deferred without blocking the first usable frontend slice:

- `GET /api/v1/projects/{projectCode}`
- `GET /api/v1/templates/{templateCode}`
- `GET /api/v1/admin/templates`
- `POST /api/v1/takeoffs/{takeoffId}/exports`
- `POST /api/v1/versions/{versionId}/exports`

These are still MVP features, but they do not block:

- login
- project list
- takeoff generation
- current detail
- safe line edit/delete
- revision browsing
