# Grounded discovery and speech

`parser.py` defines documented analytical English intent/constraint rules.
Catalogue resolution, PostgreSQL semantic retrieval, actual audience evidence,
hybrid preferences and bounded private context are connected in
`backend/app/services/chat.py`. No trained universal NLU or unrestricted
generative answer is claimed. See the six-query routing table and limitations
in [the through-11 runbook](../documentation/phases9-11/RUNBOOK.md).

`speech.py` loads only a reviewed, hash-checked, manually cached CTranslate2
model through optional faster-whisper1.2.1 on CPU int8. Text is always available.
Model permission fields: `model_license_reviewed:true`, `license_reference`,
`model_revision`, and `files_sha256` for every relative local model file.
No permission/checkpoint file is fabricated by source generation. No speech
package/model is automatically installed, fetched or loaded during imports.

Set private `SPEECH_MODEL_PATH` and `SPEECH_PERMISSION_PATH` only when genuine
inputs exist. Optional packages are declared in
`requirements/requirements-speech.txt`; this candidate manifest is not a tested
transitive lock. The PyTorch CUDA runtime does not certify CTranslate2 GPU use.
