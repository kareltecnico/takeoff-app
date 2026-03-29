export type StructureType = 'TH' | 'Villas' | 'SFH' | 'Custom'

export type BaselineOption = {
  id: string
  structureType: Exclude<StructureType, 'Custom'>
  label: string
  description: string
  templateCode: 'TH_STANDARD' | 'VILLA_1331' | 'VILLA_STANDARD' | 'SF_GENERIC'
}

export type StandardItemKey =
  | 'kitchenFaucet'
  | 'garbageDisposal'
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

export const STANDARD_ITEM_OPTIONS: Record<StandardItemKey, StandardItemOption[]> = {
  kitchenFaucet: [{ code: 'XPLBFMKF0032', label: 'Kitchen Faucet' }],
  garbageDisposal: [{ code: 'XPLBFGD00006', label: 'Garbage Disposal' }],
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

export function findBaselineByTemplateCode(templateCode: string | null | undefined) {
  return BASELINE_OPTIONS.find((option) => option.templateCode === templateCode) ?? null
}

export function findBaselineById(id: string | null | undefined) {
  return BASELINE_OPTIONS.find((option) => option.id === id) ?? null
}
