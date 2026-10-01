$ErrorActionPreference = 'Stop'
$Ex = 'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\execution'
$Prep = Join-Path $Ex 't6_recovery_preparation_20260929_1548'
$Out = $PSScriptRoot
$Destination = Join-Path $Out 'RELEASE_CONTRACT_REVIEW.json'
if (Test-Path -LiteralPath $Destination) { throw 'Review already sealed; no overwrite' }
function Bind-Small([string]$Path) {
    $Info = Get-Item -LiteralPath $Path
    if ($Info.Length -ge 16MB -or $Info.Extension -in @('.pt','.npz','.npy','.jpg','.png')) { throw 'Not a permitted small-file binding' }
    return [ordered]@{path=$Info.FullName;bytes=[long]$Info.Length;sha256=(Get-FileHash -LiteralPath $Info.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function Pin-Small([string]$Path,[string]$Sha) {
    $Row = Bind-Small $Path
    if ($Row.sha256 -cne $Sha) { throw "Unexpected reviewed bytes: $Path" }
    return $Row
}
$Candidate = Pin-Small (Join-Path $Prep 'pipeline_recovery_candidate.py') 'b95ee9ff8c90b9323b89eb3a9228c36e40576b16830eb07dbd78e38cef1f833e'
$Entry = Pin-Small (Join-Path $Prep 'start_pipeline_recovery_candidate.ps1') '3c9e1ec672f6ef7b2a33060495c26d4a766add0b74e2780cc7dc4db732d4eb37'
$Manifest = Pin-Small (Join-Path $Prep 'SOURCE_MANIFEST.json') '8cf084500ae398685ab79d629edb1f9ebffd808e28e605c104d8a93a39c52c41'
$ContractBinding = Pin-Small (Join-Path $Prep 'RECOVERY_CONTRACT.json') '01bf6d97793d0fbcda9936a85b7955b83e336d0c932531eec9f8f33b179b08a3'
$Adoption = Pin-Small (Join-Path $Prep 'ROOT_SOURCE_ADOPTION.json') 'fd093b974627d6ddd6700ffb40c071e2c28deceeb39713fbc8e4cede3dee3fe3'
$Seed = Pin-Small (Join-Path $Prep 'pipeline_seed.json') '20973168dee96357397f27d103db79eec8f71375272fd3d1e9d240487f1d4360'
$Spec = Pin-Small (Join-Path $Ex 'efficiency_incident_review_20260929_1448\RECOVERY_SPEC.json') '66e499c80036c3ef376993eb0decd01e28cd7adfa07cef54efc1001ac5dc0c45'
$Initialization = Pin-Small (Join-Path $Ex 'shared_lock_initialization_20260929_1652\ROOT_INITIALIZATION_ADOPTION.json') '7b300de0fe22577eead8e2fd844ac90283da387b572530bc1882f2f2064e0a02'
$Observation = Bind-Small (Join-Path $Ex 'efficiency_incident_20260929_1448\observation_20260929_174948645\OBSERVATION.json')
$Contract = Get-Content -LiteralPath $ContractBinding.path -Raw -Encoding UTF8 | ConvertFrom-Json
$ManifestData = Get-Content -LiteralPath $Manifest.path -Raw -Encoding UTF8 | ConvertFrom-Json
$AdoptionData = Get-Content -LiteralPath $Adoption.path -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Contract.input_bindings.Count -ne 96 -or $ManifestData.candidate_files.Count -ne 14) { throw 'Unexpected adopted contract coverage' }
if ($AdoptionData.schema -cne 't6-pipeline-recovery-source-adoption.v1' -or $AdoptionData.approved_for_future_gated_execution -ne $true -or $AdoptionData.execution_released -ne $false) { throw 'Unexpected source adoption scope' }
$Report = [ordered]@{
    schema='t6-future-release-contract-static-review.v1'
    reviewed_utc=[DateTime]::UtcNow.ToString('o')
    status='existing_candidate_sufficient_no_new_runner_required'
    is_execution_release=$false
    current_execution_approved=$false
    scope='Explain future release evidence and exact existing gates only; no launch or live mutation'
    source_and_small_file_bindings=@($Candidate,$Entry,$Manifest,$ContractBinding,$Adoption,$Seed,$Spec,$Initialization,$Observation)
    direct_release_contract=[ordered]@{
        consumed_fields=@('schema','scope','execute','source_manifest','root_adoption','issued_utc','expires_utc')
        fields=[ordered]@{
            schema=[ordered]@{type='string';required_value='t6-pipeline-recovery-release.v1'}
            scope=[ordered]@{type='string';required_value='pipeline_only_original_stage7'}
            execute=[ordered]@{type='boolean';required_value=$true;note='Description of a future release field, not authorization by this report'}
            source_manifest=[ordered]@{type='exact binding object';required_binding=$Manifest}
            root_adoption=[ordered]@{type='exact binding object';required_binding=$Adoption}
            issued_utc=[ordered]@{type='ISO 8601 timezone-aware timestamp';rule='issued <= runtime now; use explicit UTC'}
            expires_utc=[ordered]@{type='ISO 8601 timezone-aware timestamp';rule='runtime now < expires; 0 < expires-issued <= 900 seconds'}
        }
        binding_shape=@('path','bytes','sha256')
        binding_equality='Whole dictionary equality; preserve exact absolute path spelling, integer byte count and lowercase SHA256'
        cli_arguments=@('--release','--release-sha256','--root-adoption','--root-adoption-sha256')
        release_sha_rule='Hash the exact final release bytes and pass that SHA separately; no self-referential release hash field'
        root_adoption_rule='Preserve historical adoption bytes, source_manifest binding, approved_for_future_gated_execution=true and execution_released=false'
        candidate_lines=@('313-335','542-550','578-588','621-632')
        entry_lines=@('3-8','12-39','42-48')
        ttl_entry_limit='PowerShell verifies bindings/schema before guardian start; Python enforces TTL. Caller should check TTL before invoking the entry.'
    }
    indirect_contract=[ordered]@{
        chain=@('release source_manifest -> exact adopted manifest','manifest candidate_files -> recovery contract, seed, candidate and entry','recovery contract input_bindings -> original source, incident/spec and adopted evidence','contract live_state_bindings and boot -> repeated actual runtime gate')
        candidate_file_count=14
        contract_input_count=96
        fixed_state_bindings=$Contract.live_state_bindings
        fixed_boot_utc_ticks=$Contract.host_boot_utc_ticks
        fixed_primary_controller_pid=$Contract.primary_controller_pid
        recovery_spec=$Contract.recovery_spec
        incident_capture=$Contract.incident_capture
        old_closed_log_prefixes=$Contract.append_log_prefixes
        enforcement='Candidate validates exact seed derivation, unchanged first six completed jobs, failed original seventh command/source and all five current state bytes'
        candidate_lines=@('87-139','183-209','549-564','578-597')
        separate_release_state_spec_boot_fields_consumed=$false
    }
    future_root_readiness_evidence=[ordered]@{
        purpose='Fresh root decision evidence to accompany a future immutable release; runtime independently repeats its gates'
        annex_fields_are_consumed_by_candidate=$false
        minimum_review_records=@(
            'Actual UTC time and bound raw observations; all five current state SHA/size equal the fixed contract',
            'Current source manifest/root adoption/contract/seed/spec bytes still match their adopted bindings',
            'Current boot equals fixed integer UTC ticks; relevant process scan includes full command/parent/creation for any observed PID; primary numeric PID must be vacant even if reused',
            'Successful fresh nvidia-smi compute query with no nonempty rows, no desktop/unknown exemption; retain raw stdout/stderr/exit code',
            'Valid integer commit limit, committed bytes and exact available difference >= 27917287424 bytes (26 GiB)',
            'Existing carrier and initialization adoption verified; carrier existence is not acquired-lock proof',
            'No runtime_attempt directory, no original T6 output, unchanged full closed old stage-log prefixes',
            'Release scope remains pipeline original stage seven only; source adoption and historical failure records are not rewritten'
        )
        lock_carrier_path=(Join-Path $Ex 'latest_baseline_gpu.lock')
        carrier_initialization_provenance=$Initialization
        no_actual_release_path_created_by_review=$true
    }
    runtime_order=[ordered]@{
        steps=@(
            'Verify exact baseline interpreter, release/root/manifest, candidate files, 96 contract inputs, original state/spec and seed',
            'Require unused runtime_attempt; acquire existing shared/matrix/three successor/supervisor first-byte locks without creating files',
            'Perform three complete fresh gates with two 15-second intervals',
            'Run original isolated native import helper with actual environment propagation including TORCHINDUCTOR_CACHE_DIR',
            'Verify native probe numeric PIDs absent; repeat full gate and fresh release TTL',
            'Perform final full gate immediately before intent; seal final_admission, retire exact failed state and publish fixed seed exclusively',
            'Release only supervisor probe lock for cooperative handoff; launch original v2 pipeline role with frozen SHA; retain outer locks through child monitoring',
            'Close logs, bind appended ranges, retain actual captured handle/Popen exits; validate first six records and original seventh completion'
        )
        candidate_lines=@('542-567','599-610','611-628','187-209','629-658')
        future_evidence_not_required_before_same_release=@('native_environment','admission','final_admission','launch_intent','child identity/exit observations')
        reason='These are generated by the guardian after the conditional release. Using them to authorize that same release is circular.'
    }
    non_substitutable_evidence=@(
        'The current false GPU gate or any old resource snapshot is not future admission',
        'Source preparation, source adoption, synthetic controls and a persistent carrier are not native execution or GPU exclusivity',
        'Old native success, old checkpoint proofs and unchanged metadata do not prove a current environment, checkpoint bytes or scientific result',
        'PID absence is not independent exit0; numeric reuse is not the original process',
        'A launch intent or self-produced aggregate cannot prove its own release or parent exit',
        'Ready controller status is not T6 scientific artifact acceptance or successor release'
    )
    current_observation=[ordered]@{
        binding=$Observation
        root_observed_time='2026-09-29T17:49:49.0253445+01:00'
        gpu_rows=24
        original_gpu_exclusive_gate_satisfied=$false
        t6_output_exists=$false
        five_states_unchanged=$true
        two_root_CIM_scans_empty=$true
        evidence_kind='Read-only root observation supplied to this static review; not a new observation by this reviewer'
        implication='No executable release or candidate launch justified now'
    }
    retry_and_scope=[ordered]@{
        unused_attempt_path=(Join-Path $Prep 'runtime_attempt')
        any_attempt_directory_forbids_replay=$true
        pre_intent_expiry='Preserve expired release; only consider a new fresh release after confirming no attempt/child and repeating readiness observations'
        partial_intent_seed_or_spawn_failure='Preserve all evidence and require a new incident review; no rollback, deletion, replay or unseeded restart'
        successors='Not part of this release; require separate subsequent recovery preparation/adoption'
        limits=@('Cooperative filesystem CAS/lock handoff is not an atomic transaction against arbitrary writers','Hard guardian/host interruption releases OS locks; inspect surviving children before any future action','Polling only proves captured handle exits; unobserved short-lived descendants remain unknown')
        candidate_lines=@('83-84','187-209','482-539','637-690')
    }
    method=[ordered]@{
        entire_candidate_and_thin_entry_read=$true
        tests_run=$false
        candidate_or_native_executed=$false
        scientific_imports_or_GPU_queries=$false
        reviewer_CIM_queries=$false
        live_state_or_lock_mutations=$false
        release_or_intent_created=$false
        all_96_inputs_rehashed_by_this_review=$false
        limitation='This review binds cited small files and explains existing gates; it does not re-execute prior controls or certify future runtime behavior'
    }
    review_markdown=(Bind-Small (Join-Path $Out 'REVIEW.md'))
    sealing_source=(Bind-Small $PSCommandPath)
}
$Bytes = [Text.UTF8Encoding]::new($false).GetBytes(($Report | ConvertTo-Json -Depth 30) + "`n")
$Stream = [IO.File]::Open($Destination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try { $Stream.Write($Bytes,0,$Bytes.Length); $Stream.Flush($true) } finally { $Stream.Dispose() }
Bind-Small $Destination | ConvertTo-Json -Compress
