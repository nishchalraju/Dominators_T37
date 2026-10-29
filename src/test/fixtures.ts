// Synthetic data for tests. Nothing here describes a real person or a real case.
import type {
  CaseDetail,
  CaseSummary,
  DatasetStatus,
  Description,
  EngineStatus,
  Evaluation,
  Meta,
  SketchVersion,
  User,
} from '@/types/api'

const values = (pairs: [string, string][]) => pairs.map(([value, label]) => ({ value, label }))

export const META: Meta = {
  app: { name: 'SketchAssist AI', version: '3.0.0' },
  vocabulary_version: '1.1',
  attributes: [
    { key: 'apparent_gender', label: 'Apparent gender', ordered: false, schematic_supported: true, values: values([['male', 'Male'], ['female', 'Female']]) },
    { key: 'age_description', label: 'Apparent age', ordered: true, schematic_supported: true, values: values([['young_adult', 'Young adult (about 18-29)'], ['adult', 'Adult (about 30-44)'], ['middle_aged', 'Middle-aged (about 45-59)'], ['elderly', 'Elderly (60+)']]) },
    { key: 'skin_colour', label: 'Skin colour', ordered: true, schematic_supported: true, values: [
      { value: 'white', label: 'White / fair', swatch: '#F5D9C4' },
      { value: 'brown', label: 'Brown / wheatish', swatch: '#B9825A' },
      { value: 'black', label: 'Black / dark', swatch: '#704C3A' },
    ] },
    { key: 'face_shape', label: 'Face shape', ordered: false, schematic_supported: true, values: values([['oval', 'Oval'], ['round', 'Round'], ['square', 'Square']]) },
    { key: 'hair_length', label: 'Hair length', ordered: true, schematic_supported: true, values: values([['bald', 'Bald'], ['short', 'Short'], ['long', 'Long']]) },
    { key: 'hair_style', label: 'Hair style', ordered: false, schematic_supported: true, values: values([['straight', 'Straight'], ['curly', 'Curly']]) },
    { key: 'eyebrows', label: 'Eyebrow thickness', ordered: true, schematic_supported: true, values: values([['thin', 'Thin'], ['medium', 'Medium'], ['thick', 'Thick']]) },
    { key: 'eye_shape', label: 'Eye shape', ordered: false, schematic_supported: true, values: values([['almond', 'Almond'], ['round', 'Round']]) },
    { key: 'nose_shape', label: 'Nose shape', ordered: false, schematic_supported: true, values: values([['narrow', 'Narrow'], ['broad', 'Broad']]) },
    { key: 'mouth_shape', label: 'Mouth shape', ordered: false, schematic_supported: true, values: values([['thin', 'Thin lips'], ['full', 'Full lips']]) },
    { key: 'facial_hair', label: 'Facial hair', ordered: false, schematic_supported: true, values: values([['none', 'None / clean-shaven'], ['beard', 'Beard']]) },
    { key: 'glasses', label: 'Glasses', ordered: false, schematic_supported: true, values: values([['none', 'No glasses'], ['glasses', 'Wearing glasses']]) },
  ],
  languages: [
    { code: 'en', label: 'English', native_label: 'English' },
    { code: 'kn', label: 'Kannada', native_label: 'ಕನ್ನಡ' },
    { code: 'hi', label: 'Hindi', native_label: 'हिन्दी' },
  ],
  case_statuses: ['in_progress', 'under_review', 'closed'],
  max_additional_details: 300,
  parser: { name: 'rule_based_multilingual', version: '1.2.0', lexicon_status: { en: 'developer_authored', hi: 'unreviewed', kn: 'unreviewed' } },
  disclaimers: {
    preliminary: 'Preliminary investigative aid - requires human review.',
    no_identification: 'This system does not identify people.',
    responsible_use: ['Every sketch needs human review.', 'It does not identify anyone.'],
  },
  registration_open: true,
}

export const ADMIN: User = { id: 1, username: 'alice', display_name: 'Alice', role: 'admin', created_at: '2026-10-01T09:00:00Z' }
export const INVESTIGATOR: User = { id: 2, username: 'bob_second', display_name: 'Bob', role: 'investigator', created_at: '2026-10-02T09:00:00Z' }

export const CASE: CaseDetail = {
  case_id: 'SA-2026-ABC234',
  title: 'Synthetic market case',
  incident_date: '2026-10-20',
  status: 'in_progress',
  investigator_ref: 'T-100',
  investigator_name: 'Test Investigator',
  witness_name: 'Test Witness',
  created_at: '2026-10-21T08:00:00Z',
  updated_at: '2026-10-22T10:30:00Z',
  description_count: 1,
  sketch_count: 2,
  selected_sketch_id: 12,
  incident_description: 'Synthetic incident used by the tests.',
  note_count: 0,
  owner_username: 'alice',
}
export const CASE_SUMMARY: CaseSummary = { ...CASE }

export const ATTRS = { apparent_gender: 'male', face_shape: 'round', eyebrows: 'thick', glasses: 'glasses' } as Record<string, string>

const base = {
  case_id: CASE.case_id, width: 1024, height: 1024, file_size: 200_000, sha256: 'a'.repeat(64), additional_details: '', parent_id: null as number | null,
  parent_version_number: null as number | null, instruction_language: null as string | null, target_attribute: null as string | null,
  engine: 'schematic', engine_label: 'Schematic composite (rule-based, not AI)', is_ai_generated: false, model_name: 'schematic-renderer 1.0',
  notes: ['Schematic composite drawn by fixed rules. It is not AI-generated.'], revision_details: null, created_by: 'alice',
}
export const V1: SketchVersion = {
  ...base, id: 11, version_number: 1, kind: 'initial', instruction: '', attributes: ATTRS, is_selected: false, created_at: '2026-10-21T08:05:00Z',
  image_url: '/api/sketch-versions/11/image', thumbnail_url: '/api/sketch-versions/11/thumbnail', download_url: '/api/sketch-versions/11/image?download=true',
}
export const V2: SketchVersion = {
  ...base, id: 12, version_number: 2, kind: 'revision', instruction: 'remove the glasses', instruction_language: 'en', parent_id: 11, parent_version_number: 1,
  target_attribute: 'glasses', attributes: { ...ATTRS, glasses: 'none' }, is_selected: true, created_at: '2026-10-22T10:30:00Z',
  revision_details: { changes: [{ attribute: 'glasses', label: 'Glasses', before: 'glasses', after: 'none', evidence: 'remove the glasses', kind: 'remove', note: null }], ignored: [], notes: [] },
  image_url: '/api/sketch-versions/12/image', thumbnail_url: '/api/sketch-versions/12/thumbnail', download_url: '/api/sketch-versions/12/image?download=true',
}
export const V_AI: SketchVersion = { ...V2, id: 13, version_number: 3, engine: 'huggingface', engine_label: 'Hugging Face Inference Providers (AI)', is_ai_generated: true, model_name: 'Qwen/Qwen-Image-Edit', is_selected: false }

export const DESCRIPTION: Description = {
  id: 5, label: 'Witness 1', language: 'en', original_text: 'A man with a round face and thick eyebrows. He wears glasses.',
  extracted_attributes: ATTRS, confirmed_attributes: ATTRS, additional_details: '', parse_details: [], unrecognized: [], warnings: [],
  parser_version: '1.1.0', created_at: '2026-10-21T08:01:00Z', updated_at: '2026-10-21T08:01:00Z', review_status: 'parser_output',
}

const engine = (over: Partial<EngineStatus>): EngineStatus => ({
  engine: 'x', label: 'X', is_ai: true, state: 'setup_required', available: false, detail: 'No token is configured.', setup_steps: ['Create a token.'],
  supports_generate: true, supports_edit: true, models: { generate: 'm' }, licence_note: null, verified: false, last_success_at: null, last_error: null,
  last_error_at: null, last_evaluated_at: null, ...over,
})
export const ENGINES_NO_AI: EngineStatus[] = [
  engine({ engine: 'schematic', label: 'Schematic composite (rule-based, not AI)', is_ai: false, state: 'ready', available: true, detail: 'Always available.', setup_steps: [], verified: true, last_success_at: '2026-10-22T10:30:00Z' }),
  engine({ engine: 'huggingface', label: 'Hugging Face Inference Providers (AI)', models: { generate: 'Qwen/Qwen-Image', edit: 'Qwen/Qwen-Image-Edit' } }),
  engine({ engine: 'openai', label: 'OpenAI Images API (AI)' }),
  engine({ engine: 'diffusers', label: 'Local diffusers model (AI, experimental)' }),
]
export const ENGINES_WITH_AI: EngineStatus[] = ENGINES_NO_AI.map((e) => (e.engine === 'huggingface' ? { ...e, state: 'ready', available: true, detail: 'Token configured.' } : e))

const dataset = (over: Partial<DatasetStatus>): DatasetStatus => ({
  key: 'cufs', name: 'CUHK Face Sketch Database (CUFS)', kind: 'external', description: 'Photo-sketch pairs.', licence: 'Research use only.', access: 'Request from the authors.',
  citation: 'Wang and Tang, 2009.', source_url: 'https://example.org/cufs', expected_path: 'backend/datasets/external/cufs/', installed: false, inspected: false,
  last_inspected_at: null, files_found: null, records: 0, valid_records: 0, labelled_records: 0, notes: ['Not installed: this application never downloads restricted datasets.'], translation_review: null, ...over,
})
export const DATASETS_EMPTY: DatasetStatus[] = [
  dataset({}),
  dataset({ key: 'cufsf', name: 'CUHK Face Sketch FERET Database (CUFSF)' }),
  dataset({ key: 'uom_sgfs', name: 'UoM-SGFS' }),
  dataset({ key: 'custom_attributes', name: 'Custom attribute dataset (synthetic demo)', kind: 'custom', installed: true, notes: [] }),
]

export const EVALUATION: Evaluation = {
  id: 1, evaluation_type: 'description_parser', target_name: 'rule_based_multilingual', target_version: '1.1.0 (word lists: en=developer_authored, hi=unreviewed, kn=unreviewed)',
  dataset_name: 'custom_attributes (synthetic demo)', dataset_version: 'abc123def456', split: 'all', n_examples: 72, status: 'completed', created_at: '2026-10-22T11:00:00Z', notes: null,
  metrics: {
    n_examples: 72, exact_match: 0.9583, micro_precision: 0.9984, micro_recall: 0.9961,
    per_attribute: [{ attribute: 'glasses', label: 'Glasses', n_gold: 30, tp: 30, fp: 0, fn: 0, accuracy: 1, precision: 1, recall: null }],
    by_language: [
      { language: 'en', n: 24, exact_match: 0.9167, mean_attribute_accuracy: 0.992, lexicon_review_status: 'developer_authored', translation_reviewed_n: 0 },
      { language: 'hi', n: 24, exact_match: 1, mean_attribute_accuracy: 1, lexicon_review_status: 'unreviewed', translation_reviewed_n: 0 },
    ],
    cross_language_agreement: { groups: 24, agreement: 0.989 },
    failures_listed: [{ sample_id: 'G10-en', language: 'en', wrong: [{ attribute: 'age_description', expected: 'adult', got: null }] }],
    caveats: ['The examples were written by the same developer who wrote the parser.'],
  },
}
