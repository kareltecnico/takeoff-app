export type StructureType = 'TH' | 'Villas' | 'SFH' | 'Custom'
export type Stage = 'ground' | 'topout' | 'final'

export type BaselineOption = {
  id: string
  structureType: Exclude<StructureType, 'Custom'>
  label: string
  description: string
  templateCode: 'TH_STANDARD' | 'VILLA_1331' | 'VILLA_STANDARD' | 'SF_GENERIC'
}

export type PlanQuantityKey =
  | 'kitchens'
  | 'garbage_disposals'
  | 'lav_faucets'
  | 'toilets'
  | 'showers'
  | 'bathtubs'
  | 'half_baths'
  | 'double_bowl_vanities'
  | 'hose_bibbs'
  | 'ice_makers'
  | 'water_heater_tank_qty'
  | 'water_heater_tankless_qty'

export type StandardItemKey =
  | 'kitchenFaucet'
  | 'garbageDisposal'
  | 'installDishwasher'
  | 'lavFaucet'
  | 'toilet'
  | 'showerTrim'
  | 'tubShowerTrim'
  | 'bathTub'
  | 'pedestal'
  | 'hoseBibb'
  | 'iceMaker'
  | 'tankWaterHeater'
  | 'tanklessWaterHeater'

export type StandardItemOption = {
  code: string
  label: string
}

export type StandardRowDefinition = {
  key: StandardItemKey
  label: string
  quantityKey: PlanQuantityKey
  category: string
  stage: Stage
  helpText?: string
}

export const STRUCTURE_OPTIONS: Array<{
  key: StructureType
  label: string
  description: string
}> = [
  {
    key: 'TH',
    label: 'TH',
    description: 'Townhome baseline workflow',
  },
  {
    key: 'Villas',
    label: 'Villas',
    description: 'Validated Villas baseline variants',
  },
  {
    key: 'SFH',
    label: 'SFH',
    description: 'Single-family baseline workflow',
  },
  {
    key: 'Custom',
    label: 'Custom',
    description: 'No baseline preloaded',
  },
]

export const BASELINE_OPTIONS: BaselineOption[] = [
  {
    id: 'th-standard',
    structureType: 'TH',
    label: 'Standard',
    description: 'Official TH baseline v1',
    templateCode: 'TH_STANDARD',
  },
  {
    id: 'villa-1331',
    structureType: 'Villas',
    label: '1331',
    description: 'Official Villas 1331 baseline',
    templateCode: 'VILLA_1331',
  },
  {
    id: 'villa-standard',
    structureType: 'Villas',
    label: '1413 / 1483 / 1521 / 1588',
    description: 'Official shared Villas family baseline',
    templateCode: 'VILLA_STANDARD',
  },
  {
    id: 'sf-standard',
    structureType: 'SFH',
    label: 'Standard',
    description: 'Official SF generic baseline',
    templateCode: 'SF_GENERIC',
  },
]

export const STANDARD_ITEM_ROWS: StandardRowDefinition[] = [
  {
    key: 'kitchenFaucet',
    label: 'Kitchen Faucet',
    quantityKey: 'kitchens',
    category: 'Kitchen Faucet',
    stage: 'final',
  },
  {
    key: 'garbageDisposal',
    label: 'Garbage Disposal',
    quantityKey: 'garbage_disposals',
    category: 'Garbage Disposal',
    stage: 'final',
  },
  {
    key: 'installDishwasher',
    label: 'Install Dishwasher',
    quantityKey: 'kitchens',
    category: 'Install Dishwasher',
    stage: 'final',
    helpText: 'Visible explicitly in the wizard. Current backend generation still derives this from kitchen count.',
  },
  {
    key: 'iceMaker',
    label: 'Ice Maker',
    quantityKey: 'ice_makers',
    category: 'Ice Maker',
    stage: 'topout',
    helpText: 'Defaults to 1 because the primary kitchen usually carries one refrigerator water connection.',
  },
  {
    key: 'lavFaucet',
    label: 'Lavatory Faucet',
    quantityKey: 'lav_faucets',
    category: 'Lav Faucet',
    stage: 'final',
  },
  {
    key: 'toilet',
    label: 'Toilets',
    quantityKey: 'toilets',
    category: 'Toilet',
    stage: 'final',
  },
  {
    key: 'showerTrim',
    label: 'Shower Trim',
    quantityKey: 'showers',
    category: 'Shower Trim',
    stage: 'final',
  },
  {
    key: 'tubShowerTrim',
    label: 'Tub & Shower Trim',
    quantityKey: 'bathtubs',
    category: 'Tub Shower Trim',
    stage: 'final',
  },
  {
    key: 'bathTub',
    label: 'Bathtub',
    quantityKey: 'bathtubs',
    category: 'Bathtub',
    stage: 'topout',
  },
  {
    key: 'pedestal',
    label: 'Pedestal',
    quantityKey: 'half_baths',
    category: 'Pedestal',
    stage: 'final',
    helpText: 'Use as a suggestion, not a hard rule. The wizard can hint when the fixture mix looks like a half-bath pattern.',
  },
  {
    key: 'hoseBibb',
    label: 'Hose Bibbs',
    quantityKey: 'hose_bibbs',
    category: 'Hose Bibb',
    stage: 'topout',
  },
]

export const STANDARD_ITEM_OPTIONS: Record<StandardItemKey, StandardItemOption[]> = {
  kitchenFaucet: [{ code: 'XPLBFMKF0032', label: 'Kitchen Faucet' }],
  garbageDisposal: [{ code: 'XPLBFGD00006', label: 'Garbage Disposal' }],
  installDishwasher: [{ code: 'LW50L80550', label: 'Install Dishwasher' }],
  lavFaucet: [{ code: 'XPLBFMLF0003', label: 'Lav Faucet' }],
  toilet: [{ code: 'XPLBF0TC0022', label: 'Toilet' }],
  showerTrim: [{ code: 'XPLBFMST0148', label: 'Shower Trim' }],
  tubShowerTrim: [{ code: 'XPLBFMTST074', label: 'Tub & Shower Trim' }],
  bathTub: [{ code: 'XPLBFTBA0056', label: 'Bathtub' }],
  pedestal: [{ code: 'XPLBF0LP0033', label: 'Pedestal' }],
  hoseBibb: [{ code: 'FW50A71400', label: 'Hose Bibb' }],
  iceMaker: [{ code: 'LW50A66010', label: 'Ice Maker Box' }],
  tankWaterHeater: [{ code: 'XPLBFWHTE007', label: 'Water Heater, Tank 50 Gal' }],
  tanklessWaterHeater: [{ code: 'FW50M10226', label: 'Tankless Water Heater' }],
}

export const BASELINE_DEFAULT_ITEMS: Record<
  BaselineOption['templateCode'],
  Record<StandardItemKey, string>
> = {
  TH_STANDARD: {
    kitchenFaucet: 'XPLBFMKF0032',
    garbageDisposal: 'XPLBFGD00006',
    installDishwasher: 'LW50L80550',
    lavFaucet: 'XPLBFMLF0003',
    toilet: 'XPLBF0TC0022',
    showerTrim: 'XPLBFMST0148',
    tubShowerTrim: 'XPLBFMTST074',
    bathTub: 'XPLBFTBA0056',
    pedestal: 'XPLBF0LP0033',
    hoseBibb: 'FW50A71400',
    iceMaker: 'LW50A66010',
    tankWaterHeater: 'XPLBFWHTE007',
    tanklessWaterHeater: 'FW50M10226',
  },
  VILLA_1331: {
    kitchenFaucet: 'XPLBFMKF0032',
    garbageDisposal: 'XPLBFGD00006',
    installDishwasher: 'LW50L80550',
    lavFaucet: 'XPLBFMLF0003',
    toilet: 'XPLBF0TC0022',
    showerTrim: 'XPLBFMST0148',
    tubShowerTrim: 'XPLBFMTST074',
    bathTub: 'XPLBFTBA0056',
    pedestal: 'XPLBF0LP0033',
    hoseBibb: 'FW50A71400',
    iceMaker: 'LW50A66010',
    tankWaterHeater: 'XPLBFWHTE007',
    tanklessWaterHeater: 'FW50M10226',
  },
  VILLA_STANDARD: {
    kitchenFaucet: 'XPLBFMKF0032',
    garbageDisposal: 'XPLBFGD00006',
    installDishwasher: 'LW50L80550',
    lavFaucet: 'XPLBFMLF0003',
    toilet: 'XPLBF0TC0022',
    showerTrim: 'XPLBFMST0148',
    tubShowerTrim: 'XPLBFMTST074',
    bathTub: 'XPLBFTBA0056',
    pedestal: 'XPLBF0LP0033',
    hoseBibb: 'FW50A71400',
    iceMaker: 'LW50A66010',
    tankWaterHeater: 'XPLBFWHTE007',
    tanklessWaterHeater: 'FW50M10226',
  },
  SF_GENERIC: {
    kitchenFaucet: 'XPLBFMKF0032',
    garbageDisposal: 'XPLBFGD00006',
    installDishwasher: 'LW50L80550',
    lavFaucet: 'XPLBFMLF0003',
    toilet: 'XPLBF0TC0022',
    showerTrim: 'XPLBFMST0148',
    tubShowerTrim: 'XPLBFMTST074',
    bathTub: 'XPLBFTBA0056',
    pedestal: 'XPLBF0LP0033',
    hoseBibb: 'FW50A71400',
    iceMaker: 'LW50A66010',
    tankWaterHeater: 'XPLBFWHTE007',
    tanklessWaterHeater: 'FW50M10226',
  },
}

export const PREVIEW_ITEM_CATEGORIES = [
  ...new Set([
    ...STANDARD_ITEM_ROWS.map((row) => row.category),
    'Per Fixture Material',
    'Per Fixture Labor',
    'Double Bowl Material',
    'Double Bowl Labor',
    'Sewer Line Material',
    'Sewer Line Labor',
    'Water Line Material',
    'Water Line Labor',
    'Plumbing Permit',
  ]),
]

export const WATER_HEATER_ITEM_CATEGORIES = [
  'Install Water Heater',
  'Tankless Water Heater',
  'Install Tankless Water Heater',
] as const

export const ITEM_CATEGORY_OPTIONS = [...new Set([...PREVIEW_ITEM_CATEGORIES, ...WATER_HEATER_ITEM_CATEGORIES])]

export const ITEM_TOOL_CATEGORY_OPTIONS = [
  'Tank Water Heater',
  'Tankless Water Heater',
  'Kitchen Faucet',
  'Lav Faucet',
  'Garbage Disposal',
  'Toilet',
  'Shower Trim',
  'Tub Shower Trim',
  'Pedestal',
  'Bathtub',
  'Hose Bibb',
  'Ice Maker',
] as const

export function findBaselineByTemplateCode(templateCode: string | null | undefined) {
  return BASELINE_OPTIONS.find((option) => option.templateCode === templateCode) ?? null
}

export function findBaselineById(id: string | null | undefined) {
  return BASELINE_OPTIONS.find((option) => option.id === id) ?? null
}
