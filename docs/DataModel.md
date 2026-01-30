{\rtf1\ansi\ansicpg1252\cocoartf2867
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 # Data Model \'97 Take-Off App (SQLite)\
\
## 1. Principles\
\
- Use a stable internal identifier for items: `internal_item_code` (unique).\
- Keep CURRENT takeoffs editable and store immutable snapshots as versions.\
- Store taxable as a per-line/per-item flag (tax rate fixed but applicability varies).\
- Preserve line ordering using `sort_order` so PDFs match the current standard format.\
\
## 2. Entities (MVP)\
\
### 2.1 Project\
Represents a Lennar (or other contractor) project/community.\
\
**Fields**\
- id (PK)\
- contractor_name (string) \'97 MVP uses string, can normalize later\
- project_name (string, required)\
- status (enum: in_course | closed) \'97 used for future price automation\
- created_at (datetime)\
- updated_at (datetime)\
\
### 2.2 Item (Item Catalog)\
Master list of items used across takeoffs.\
\
**Fields**\
- id (PK)\
- internal_item_code (string, UNIQUE, required)\
- lennar_item_number (string, nullable)\
- description1 (string, required)\
- description2 (string, nullable)\
- unit (string, e.g., EA, LF)\
- item_type (enum: material | service)\
- default_taxable (bool)\
- created_at (datetime)\
- updated_at (datetime)\
\
Notes:\
- Some \'93material-like\'94 billing lines may still be `default_taxable = false` due to agreements.\
\
### 2.3 Model Template\
Reusable template per model.\
\
**Fields**\
- id (PK)\
- template_name (string, required) \'97 e.g., "1331", "TH-DEFAULT"\
- construction_type (string, optional) \'97 TH/Villas/SFH (optional helper)\
- default_stories (int, nullable)\
- created_at (datetime)\
- updated_at (datetime)\
\
### 2.4 Model Template Line\
The default line items that a model template loads into a takeoff.\
\
**Fields**\
- id (PK)\
- model_template_id (FK -> ModelTemplate.id)\
- item_id (FK -> Item.id)\
- stage (enum: ground | topout | final)\
- default_qty_rule (string or JSON) \'97 can be "from_counts:fixture_count" etc.\
- default_factor (float) \'97 0.3 / 0.4 / 1.0\
- taxable_override (bool, nullable) \'97 optional override over Item.default_taxable\
- sort_order (int) \'97 ensures stable ordering\
- notes (string, nullable)\
\
### 2.5 Model Group Template (Optional but recommended)\
A reusable set of models frequently grouped together.\
\
**Fields**\
- id (PK)\
- name (string, required) \'97 e.g., "KEYS GATE II TH GROUP A"\
- model_group_display (string, required) \'97 e.g., "1333-1455-1588"\
- models_json (text JSON array) \'97 ["1333","1455","1588"]\
- created_at, updated_at\
\
### 2.6 Takeoff (CURRENT)\
Editable working takeoff.\
\
**Fields**\
- id (PK)\
- project_id (FK -> Project.id)\
- model_group_display (string, required) \'97 printed on PDF\
- models_json (text JSON array) \'97 used for search by single model\
- stories (int, required)\
- counts_json (text JSON object) \'97 fixture_count, distances, tubs, etc.\
- created_at, updated_at\
\
### 2.7 Takeoff Line (CURRENT)\
Line items for CURRENT takeoff.\
\
**Fields**\
- id (PK)\
- takeoff_id (FK -> Takeoff.id)\
- stage (enum: ground | topout | final)\
- item_id (FK -> Item.id)\
- item_number_override (string, nullable)\
- description1_override (string, nullable)\
- description2_override (string, nullable)\
- unit_override (string, nullable)\
- price (decimal, required)\
- qty (decimal, required)\
- factor (decimal, required) \'97 0.3 / 0.4 / 1.0\
- taxable (bool, required)\
- sort_order (int, required)\
- created_at, updated_at\
\
### 2.8 Takeoff Version (Snapshot)\
Immutable snapshot label for the takeoff at a point in time.\
\
**Fields**\
- id (PK)\
- takeoff_id (FK -> Takeoff.id)\
- version_no (int, required) \'97 1,2,3...\
- created_at (datetime)\
- notes (string, nullable)\
\
### 2.9 Takeoff Version Line (Snapshot Lines)\
Copy of Takeoff Lines at snapshot time.\
\
**Fields**\
- id (PK)\
- takeoff_version_id (FK -> TakeoffVersion.id)\
- stage\
- internal_item_code (string) \'97 store for traceability\
- item_number\
- description1\
- description2\
- unit\
- price\
- qty\
- factor\
- taxable\
- sort_order\
\
Rationale:\
- Store denormalized values so a version never changes, even if the item catalog changes later.\
\
### 2.10 Settings\
Key-value settings.\
\
**Fields**\
- key (PK string)\
- value (string)\
\
Initial settings:\
- TAX_RATE = "0.07"\
- VALVE_DISCOUNT = "-112.99"\
\
## 3. Relationships\
\
- Project 1\'97* Takeoff\
- Takeoff 1\'97* TakeoffLine\
- Takeoff 1\'97* TakeoffVersion\
- TakeoffVersion 1\'97* TakeoffVersionLine\
- Item 1\'97* ModelTemplateLine\
- ModelTemplate 1\'97* ModelTemplateLine\
\
## 4. Totals Computation (per line)\
\
For a given line:\
- line_subtotal = price * qty * factor\
- tax_amount = line_subtotal * TAX_RATE if taxable else 0\
- line_total = line_subtotal + tax_amount\
\
Stage totals:\
- stage_subtotal = sum(line_subtotal)\
- stage_tax = sum(tax_amount)\
- stage_total = stage_subtotal + stage_tax\
\
Grand totals:\
- grand_subtotal = sum(stage_subtotal)\
- grand_tax = sum(stage_tax)\
- grand_total = grand_subtotal + grand_tax\
- grand_total_after_discount = grand_total + VALVE_DISCOUNT\
\
## 5. Future extensions (v1.1 / v2)\
\
### v1.1 Pricing policies\
- PriceList\
- PriceListItem\
- ProjectPricePolicy\
- ProjectPriceOverride\
\
### v2 Upgrades\
- UpgradeSet (project/model group)\
- UpgradeLine (add/remove delta lines by area)}