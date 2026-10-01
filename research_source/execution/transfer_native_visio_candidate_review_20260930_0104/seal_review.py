"""Seal this independent source review; no producer execution."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

R = Path(__file__).resolve().parent
OUT = R.parent.parent
NEW = OUT / 'transfer_native_visio_candidate_20260930_0104'
OBS = R.parent / 'heartbeat_observation_20260930_0102'


def desc(p):
    p = Path(p)
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def save(p, v):
    with Path(p).open('x', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(v, ensure_ascii=False, indent=2) + '\n')


source = desc(NEW / 'build_visio_broker_candidate.ps1')
assert source['sha256'] == '248845f8272306897369f2501e6fcce5a7d347cff4cab873d9c995ee65bc35b1'
static = load(R / 'STATIC_BINDINGS_REVIEW.json')
predicates = load(R / 'BROKER_PREDICATE_REVIEW.json')
assert static['passed'] and predicates['passed']
assert static['source'] == source and predicates['candidate'] == source
observation = load(OBS / 'OBSERVATION_WRAPPER_INCLUDED.json')
visio = [p for p in observation['second']['matches'] if p['name'] == 'VISIO.EXE']
assert len(visio) == 1 and visio[0]['pid'] == 14932 and visio[0]['creation_utc_ticks'] == '639263209854724070'
assert not (NEW / 'runtime_attempt_v1').exists()

conclusions = [
    {'area': 'Old and new source', 'result': 'Read the full executed predecessor, full final 281-line candidate, complete predecessor-to-candidate diff, scope-decision diff, manifest and input contract. Independent reconstruction of the complete diff matches exactly. Exact predecessor SHA remains 21b292f9...; candidate drawing and reopen/export blocks remain byte-identical.'},
    {'area': 'Durable unconfirmed identity', 'lines': [15, 16, 49, 56, 83, 88, 93, 100, 136, 169], 'result': 'CreateNew event files use Flush(true) and close. Entry builder actual executable, command, parent, CIM creation and held process ticks are recorded before initial Visio rejection. Creation lower/upper bounds, HWND-derived OS PID, raw process fields and held ticks are recorded as acquired before their rejection gates. Ownership remains false through the all-gates-passed durable event; a failure to save it prevents ownership. Missing/unavailable evidence is never inferred.'},
    {'area': 'Existing applications', 'lines': [61, 66, 67, 85, 182, 183], 'result': 'Initial and each immediate pre-creation Visio inventories must be empty. No existing-instance attachment API, GetActiveObject, Kill or Stop-Process route exists. References, ownership and held handle are reset per creation purpose. The known existing unconfirmed PID14932 is not accepted, adopted or cleaned by this candidate.'},
    {'area': 'Parent proof', 'lines': [42, 77, 81, 82, 102, 109, 112, 117, 119, 131, 134], 'result': 'Direct parenting to the current builder uses its held/CIM creation identity with fresh/final CIM identity checks. Alternative parenting requires the dynamically queried exact DcomLaunch service, Running, LocalSystem, its exact configured System32 svchost executable and -k DcomLaunch -p arguments, matching candidate parent PID, and stable parent PID/name/creation before COM, after COM, fresh recheck and final recheck. No hard-coded broker PID or generic svchost acceptance is present. Required service/process/creation proof is checked before COM.'},
    {'area': 'Broker proof scope', 'result': 'This is service configuration plus dynamic SCM process mapping plus CIM parent creation/name evidence. It is not held-handle or actual-image verification of the broker. Null actual executable/command remain null and explicitly unverified. If actual executable is nonempty, it must match the expected system executable. Service PathName is never substituted into actualCommandLine or actual executable. Original FAILURE_ANALYSIS minimum does not require an actual broker kernel image query or broker held handle.'},
    {'area': 'Preserved Visio gates', 'lines': [89, 93, 96, 97, 100, 101, 122, 124, 126, 128, 136, 137], 'result': 'HWND to OS PID, non-preexisting PID, VISIO.EXE CIM identity, held/CIM creation equality, bounded creation call, exact Office16 executable, complete Automation/Invisible/Embedding command, invisible state and zero documents all precede ownership and Documents.Add. Service proof does not replace any of these gates.'},
    {'area': 'Cleanup and log failures', 'lines': [141, 148, 152, 154, 157, 162, 247, 249, 258, 263, 273], 'result': 'The discovered document-close failure path is fixed: its separate catch cannot skip later application cleanup. Confirmed Quit failure still attempts reference release and held-process exit observation; detailed Quit/release/wait results are logged only after these steps. Unknown references get only a release attempt, never Quit; release success/failure is labeled accurately. Logger failure after release cannot prevent the completed release, and a logger failure during identity confirmation reaches outer cleanup with the actual ownership flag. BUILD_FAILURE is attempted after finally. No forced termination occurs; a failed filesystem write can still prevent a final report, so absent logs are not proof of exit. Cleanup branches were inspected statically, not executed.'},
    {'area': 'One-shot and data scope', 'lines': [3, 5, 6, 174, 175, 178, 180, 181, 187, 233], 'result': 'A new explicit flag is required, and any existing runtime_attempt_v1 directory rejects replay even if no terminal report was written. Runtime output is isolated from predecessor files. Source files, specification, provenance, 20 adopted inputs and 2 notes are hashed before use; all pins independently match. The unchanged drawing/export blocks retain native primitives, Arial minimum 8 pt, exact input mapping and notes, saved-file reopen, PNG/PDF exports and output collision rejection. Old CPU/success reports are not adopted as evidence for this candidate.'},
    {'area': 'Narrow validation', 'result': 'Independent small-file binding and complete-diff/block checks passed. Candidate syntax was parsed without executing it. Eleven fixtures evaluated only the ten original Boolean broker argument expressions extracted from its AST: correct null actual fields and matching available image were accepted; wrong available image, changed parent creation/PID, non-Running, wrong account, wrong config/name and recheck changes were rejected. This is expression validation, not execution of IdentityGate/NewOwnedApp, the builder, a Windows branch or cleanup.'},
]
review = {
    'schema': 'independent-t3-visio-candidate-source-review.v1',
    'utc': datetime.now(timezone.utc).isoformat(),
    'verdict': 'SOURCE_REVIEW_PASS_NOT_EXECUTION_APPROVAL',
    'source': source,
    'manifest': desc(NEW / 'CANDIDATE_SOURCE_MANIFEST.json'),
    'completeDiff': desc(NEW / 'PREDECESSOR_TO_CANDIDATE.patch'),
    'conclusions': conclusions,
    'openSourceFindings': [],
    'resolvedFindings': [
        'After-COM actual broker image requirement in first draft was replaced by the explicitly limited original service-mapping/creation proof, with required preflight before COM and nullable actual fields preserved.',
        'Initial rejection now records actual builder identity before the initial existing-Visio gate.',
        'Document-close and Quit failures no longer skip the subsequent reference cleanup steps.'
    ],
    'draftFindingDisposition': 'DRAFT_FINDING.json and first-read draft remain unchanged historical evidence. Its suggested held broker image query was optional advice, superseded by root selecting the original minimum service/SCM/CIM scope. The root read-only OpenProcess error5 is retained as unavailable actual-image evidence, never as a permission bypass, execution attempt, or ownership proof.',
    'currentExecutionBlock': {
        'rootObservation': desc(OBS / 'OBSERVATION_WRAPPER_INCLUDED.json'),
        'observedUTC': observation['second']['observed_utc'],
        'existingUnconfirmedVisio': visio,
        'decision': 'No COM invocation, attach, retry or cleanup is approved. Existing Visio still blocks the candidate. Any future execution requires a separate root decision and fresh observations; this review grants none.'
    },
    'brokerDiagnostic': desc(OBS / 'BROKER_QUERY_IMAGE_OBSERVATION.json'),
    'originalFailureAnalysis': desc(R.parent / 'transfer_native_visio_review_20260930_0006' / 'FAILURE_ANALYSIS.md'),
    'validation': [desc(R / 'STATIC_BINDINGS_REVIEW.json'), desc(R / 'BROKER_PREDICATE_REVIEW.json')],
    'COMExecuted': False, 'CIMQueriedByReviewer': False, 'cleanupExecuted': False,
    'producerCheckerExecuted': False, 'priorSuitesRerun': False, 'scientificExecution': False,
    'executionApproved': False, 'artifactAdoptionApproved': False,
    'nativeArtifactsGenerated': False, 'visualReviewPerformed': False,
}
save(R / 'PREEXEC_SOURCE_REVIEW.json', review)
md = f"""# Independent T3 Visio candidate source review

Verdict: **SOURCE_REVIEW_PASS_NOT_EXECUTION_APPROVAL**. The final 27,526-byte candidate has SHA256 `{source['sha256']}`. No remaining source blocker was found within the original failure-analysis contract. This does not authorize COM execution, attachment, retry, or cleanup. Root's bound observation still contains unconfirmed Visio PID 14932, creation ticks 639263209854724070; the candidate must reject any existing Visio.

The full old and new source and complete diff were read. Independent reconstruction matches the complete diff, all small-file pins match, and the entire drawing and saved-file reopen/export blocks are unchanged. The original input specification, provenance, 20 adopted source files and two notes remain bound. No scientific or prior 800/1247 checks were rerun.

The candidate writes CreateNew identity events with a durable flush. It records actual builder identity before the initial rejection, then records available unconfirmed candidate facts before identity gates. A failed log before ownership stops confirmation. All prior Visio gates remain: HWND to actual Windows PID, new process, held/CIM creation equality, creation interval, exact Office16 executable/full command, invisible state and zero documents. Ownership is set only after the durable all-gates-passed event.

The broker alternative is limited to exact Running/LocalSystem DcomLaunch configuration, dynamic SCM PID mapping and stable parent CIM name/creation across pre/post/fresh/final checks. Nullable actual broker executable and command remain unverified; an available executable must match. Configuration is never called an observed command or image. This meets the original minimum without requiring a broker kernel handle. The read-only OpenProcess error 5 confirms that stronger observation was unavailable; it proves no candidate ownership. The earlier independent draft suggestion is preserved as history, with this scope decision superseding it.

One real cleanup defect was found and fixed during review: a document-close exception could skip application cleanup. Document cleanup is now isolated; confirmed Quit failure still attempts reference release and held-process exit observation. Detailed outcome logging follows these operations. Unknown references receive only a release attempt, accurately labeled successful or failed, and never Quit. The outer failure report is attempted after finally. Filesystem failure can still prevent a final report; missing records must never be used as exit proof. These lifecycle paths were reviewed statically, with no cleanup tests or app access.

The isolated broker check evaluates only ten original Boolean expressions extracted from the actual candidate AST with eleven synthetic dictionaries. Correct null actual fields and a matching available image pass; wrong nonempty image, parent creation/PID, service state/account/name/configuration and changed rechecks fail. It does not execute IdentityGate, NewOwnedApp, the builder, CIM, COM or cleanup. Both this limited check and independent byte/diff verification passed.

The source keeps a separate one-shot runtime namespace; any prior namespace rejects replay. Native VSDX/PNG/PDF production, runtime ownership/cleanup verification, XML semantics, visual review, packaging and adoption remain unperformed. A source review is the only outcome of this audit.

Detailed evidence: `PREEXEC_SOURCE_REVIEW.json`, `STATIC_BINDINGS_REVIEW.json`, and `BROKER_PREDICATE_REVIEW.json`. Historical `DRAFT_FINDING.json` and `DRAFT_OWNERSHIP_FIRST_READ.ps1.txt` were not rewritten. All reviewer writes are confined to this review directory.
"""
with (R / 'REVIEW.md').open('x', encoding='utf-8', newline='\n') as f:
    f.write(md)
delivery = {
    'schema': 'independent-t3-candidate-review-delivery.v1',
    'utc': datetime.now(timezone.utc).isoformat(),
    'verdict': review['verdict'], 'source': source,
    'files': [desc(p) for p in sorted(R.iterdir()) if p.is_file() and p.name != 'DELIVERY.json'],
    'executionApproved': False, 'COMExecuted': False,
}
save(R / 'DELIVERY.json', delivery)
print(json.dumps({'review': desc(R / 'PREEXEC_SOURCE_REVIEW.json'), 'delivery': desc(R / 'DELIVERY.json'), 'verdict': review['verdict']}, ensure_ascii=True))
