$ErrorActionPreference = 'Stop'
$Ex = 'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$Automation = 'C:\Users\17703\.codex\automations\automation\automation.toml'
$Destination = Join-Path $PSScriptRoot 'MANIFEST.json'
if (Test-Path -LiteralPath $Destination) { throw 'Already sealed; preserve existing manifest' }
function Binding([string]$Path) {
    $Item = Get-Item -LiteralPath $Path
    if ($Item.Length -ge 16MB) { throw 'Small-file only' }
    return [ordered]@{path=$Item.FullName;bytes=[long]$Item.Length;sha256=(Get-FileHash -LiteralPath $Item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function Pin([string]$Path,[string]$Sha) {
    $Bound = Binding $Path
    if ($Bound.sha256 -cne $Sha) { throw "Expected input changed: $Path" }
    return $Bound
}
$PromptPath = Join-Path $PSScriptRoot 'PROMPT_BASE.txt'
$Prompt = [IO.File]::ReadAllText($PromptPath,[Text.Encoding]::UTF8)
$OldLine = Get-Content -LiteralPath $Automation -Encoding UTF8 | Where-Object { $_.StartsWith('prompt = ') }
if (@($OldLine).Count -ne 1) { throw 'Unexpected automation prompt representation' }
# This existing TOML basic string is JSON-compatible; read only, never rewrite TOML.
$OldPrompt = $OldLine.Substring(9) | ConvertFrom-Json
if ($OldPrompt.Length -ne 36589) { throw 'Active prompt changed since editorial read; review before sealing' }
if ($Prompt.Length -gt 12000) { throw 'Draft exceeds target total-character budget' }
$Sha = [Security.Cryptography.SHA256]::Create()
try { $OldDigest = [Convert]::ToHexString($Sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($OldPrompt))).ToLowerInvariant() } finally { $Sha.Dispose() }
$Sources = @(
    (Binding (Join-Path $Ex 'HANDOFF.md')),
    (Binding $Automation),
    (Pin (Join-Path $Ex 'efficiency_incident_20260929_1448\observation_20260929_185602857\OBSERVATION.json') 'f7297df4176b5b876503cfcf756c02a6c7aaa1222b30731a3884415ff7ca6dfe'),
    (Pin (Join-Path $Ex 'query_t5_root_observation_20260929_1859\ROOT_STOPPED_OBSERVATION.json') '7b88bb5ab91c76d833bd1ed9158bc1a45f862420c8b2606666c7b7c5b8fb2e99'),
    (Pin (Join-Path $Ex 't6_recovery_preparation_20260929_1548\pipeline_recovery_candidate.py') 'b95ee9ff8c90b9323b89eb3a9228c36e40576b16830eb07dbd78e38cef1f833e'),
    (Pin (Join-Path $Ex 't6_recovery_preparation_20260929_1548\ROOT_SOURCE_ADOPTION.json') 'fd093b974627d6ddd6700ffb40c071e2c28deceeb39713fbc8e4cede3dee3fe3'),
    (Pin (Join-Path $Ex 't6_release_contract_review_20260929_1750\RELEASE_CONTRACT_REVIEW.json') 'e2ac6dc6a3c1068fde976458e31d0e50617c84b888611aff387b6ba76bf567cb'),
    (Pin (Join-Path $Ex 'shared_lock_initialization_20260929_1652\ROOT_INITIALIZATION_ADOPTION.json') '7b300de0fe22577eead8e2fd844ac90283da387b572530bc1882f2f2064e0a02'),
    (Pin (Join-Path $Ex 'overleaf_delivery_20260927\DELIVERY.json') 'ef843bf1ac5eb7978ecd9ac90f15bfee789e1a74028967af6762514608e1c45c')
)
$Record = [ordered]@{
    schema='heartbeat-prompt-consolidation-draft.v1'
    sealed_utc=[DateTime]::UtcNow.ToString('o')
    status='draft_for_root_review_not_applied'
    outputs=@((Binding $PromptPath),(Binding (Join-Path $PSScriptRoot 'COVERAGE.md')))
    source_bindings=$Sources
    previous_prompt=[ordered]@{utf16_characters=$OldPrompt.Length;utf8_bytes=[Text.Encoding]::UTF8.GetByteCount($OldPrompt);decoded_utf8_sha256=$OldDigest;automation_toml_read_only=$true}
    base_prompt=[ordered]@{utf16_characters=$Prompt.Length;han_characters=[regex]::Matches($Prompt,'[\p{IsCJKUnifiedIdeographs}]').Count;utf8_without_bom=$true;within_12000_total_characters=($Prompt.Length -le 12000);reduction_percent=[Math]::Round((1-$Prompt.Length/$OldPrompt.Length)*100,3)}
    retained_operational_groups=@('latest evidence and quiet notifications','actual scientific coverage and stopped states','T6 incident and used recovery bans','candidate source adoption and initialized carrier','all seven fresh-release fields and repeated live gates','frozen science and user resource limits','five serial layers plus separate extra DAC','efficiency/B1 public gates and unimplemented work','inherited-evidence and negative-result/statistical limits','accepted editable figure scopes and remaining T5/LOHO/explanation/Visio','correct existing Overleaf and final delivery condition')
    change_scope='Editorial consolidation of prior operative instructions; immutable historical evidence is referenced rather than repeated'
    pending_root_action='Review this base, append any actually adopted new T5/latest section, then apply using automation_update and verify actual saved prompt. Do not directly edit TOML.'
    t5_figure_acceptance_claimed=$false
    automation_changed=$false
    handoff_changed=$false
    new_authorization_inferred=$false
    release_intent_or_lock_created=$false
    scientific_native_candidate_or_test_execution=$false
    reviewer_CIM_or_GPU_query=$false
    sealing_source=(Binding $PSCommandPath)
}
$Bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Record | ConvertTo-Json -Depth 12) + "`n")
$Stream=[IO.File]::Open($Destination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try { $Stream.Write($Bytes,0,$Bytes.Length); $Stream.Flush($true) } finally { $Stream.Dispose() }
Binding $Destination | ConvertTo-Json -Compress
