$ErrorActionPreference = 'Stop'
$reviewRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$candidatePath = 'C:\OneDrive\文档\LGM-GAME\outputs\paper_evidence_rebuild_20260914\transfer_native_visio_candidate_20260930_0104\build_visio_broker_candidate.ps1'
$tokens = $null; $parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($candidatePath,[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count){throw ($parseErrors | Out-String)}
$names = @('broker_preflight_service_count','broker_preflight_service','broker_preflight_parent','broker_service_count','broker_service_running_account','broker_service_parent_pid','broker_service_configuration','broker_parent_process','broker_fresh_recheck','final_broker_parent_recheck')
$expressions = [ordered]@{}
foreach($name in $names){
    $matching = @($ast.FindAll({param($node) $node -is [System.Management.Automation.Language.CommandAst] -and $node.GetCommandName() -eq 'IdentityGate' -and $node.CommandElements[1].Value -eq $name},$true))
    if($matching.Count -ne 1){throw "Expected exactly one original gate: $name"}
    $expression = $matching[0].CommandElements[2].Extent.Text
    $localTokens = $null; $localErrors = $null
    $expressionAst = [System.Management.Automation.Language.Parser]::ParseInput($expression,[ref]$localTokens,[ref]$localErrors)
    if($localErrors.Count){throw "Expression parse failed: $name"}
    $commands = @($expressionAst.FindAll({param($node) $node -is [System.Management.Automation.Language.CommandAst]},$true))
    if($commands.Count){throw "Non-pure command in isolated expression: $name"}
    $invocations = @($expressionAst.FindAll({param($node) $node -is [System.Management.Automation.Language.InvokeMemberExpressionAst]},$true))
    foreach($invocation in $invocations){
        if($invocation.Member.Value -ne 'Equals' -or $invocation.Expression.Extent.Text -ne '[string]'){throw "Unexpected member call: $name"}
    }
    $expressions[$name] = [ordered]@{expression=$expression;line=$matching[0].Extent.StartLineNumber}
}
function ServiceFixture { [ordered]@{name='DcomLaunch';state='Running';startName='LocalSystem';processId=2232;configuredPathName='C:\Windows\System32\svchost.exe -k DcomLaunch -p'} }
function ParentFixture { [ordered]@{pid=2232;name='svchost.exe';ticks='1000';executable=$null;actualCommandLine=$null} }
function BrokerFixture { [ordered]@{services=@((ServiceFixture));parent=(ParentFixture)} }
$cases = @(
    [ordered]@{name='null_actual_fields_correct_dynamic_binding';accepted=$true},
    [ordered]@{name='matching_available_actual_image';accepted=$true},
    [ordered]@{name='wrong_nonempty_actual_image';accepted=$false},
    [ordered]@{name='changed_parent_creation';accepted=$false},
    [ordered]@{name='changed_service_pid';accepted=$false},
    [ordered]@{name='service_not_running';accepted=$false},
    [ordered]@{name='service_not_LocalSystem';accepted=$false},
    [ordered]@{name='wrong_service_configuration';accepted=$false},
    [ordered]@{name='wrong_service_name';accepted=$false},
    [ordered]@{name='fresh_recheck_changed_creation';accepted=$false},
    [ordered]@{name='final_recheck_wrong_actual_image';accepted=$false}
)
$results = [Collections.Generic.List[object]]::new()
foreach($case in $cases){
    $broker0=BrokerFixture; $broker=BrokerFixture; $again=BrokerFixture; $finalBroker=BrokerFixture
    $script:candidate=[ordered]@{brokerBefore=$broker0}
    $p=[ordered]@{ParentProcessId=2232}; $ct=[int64]2000
    $systemExe='C:\Windows\System32\svchost.exe'
    $configPattern='^"?'+[regex]::Escape($systemExe)+'"?\s+-k\s+DcomLaunch\s+-p\s*$'
    switch($case.name){
        'matching_available_actual_image' { foreach($b in @($broker0,$broker,$again,$finalBroker)){$b.parent.executable=$systemExe} }
        'wrong_nonempty_actual_image' { $broker.parent.executable='C:\Other\svchost.exe' }
        'changed_parent_creation' { $broker.parent.ticks='1010' }
        'changed_service_pid' { $broker.services[0].processId=2233 }
        'service_not_running' { $broker.services[0].state='Stopped' }
        'service_not_LocalSystem' { $broker.services[0].startName='LocalService' }
        'wrong_service_configuration' { $broker.services[0].configuredPathName='C:\Windows\System32\svchost.exe -k OtherService -p' }
        'wrong_service_name' { $broker.services[0].name='OtherService' }
        'fresh_recheck_changed_creation' { $again.parent.ticks='1010' }
        'final_recheck_wrong_actual_image' { $finalBroker.parent.executable='C:\Other\svchost.exe' }
    }
    $svc0=$broker0.services[0]; $bp0=$broker0.parent
    $svc=$broker.services[0]; $beforeSvc=$broker0.services[0]; $bp=$broker.parent
    $evaluations=[Collections.Generic.List[object]]::new()
    foreach($entry in $expressions.GetEnumerator()){
        $value = & ([scriptblock]::Create($entry.Value.expression))
        if($value -isnot [bool]){throw "Non-Boolean isolated result: $($entry.Key)"}
        $evaluations.Add([ordered]@{gate=$entry.Key;passed=$value})
    }
    $accepted=@($evaluations | Where-Object {!$_.passed}).Count -eq 0
    $results.Add([ordered]@{case=$case.name;expectedAccepted=$case.accepted;actualAccepted=$accepted;passed=($accepted -eq $case.accepted);evaluations=$evaluations})
}
$report=[ordered]@{
    schema='independent-isolated-broker-predicate-review.v1'
    utc=[DateTimeOffset]::UtcNow.ToString('o')
    candidate=[ordered]@{path=$candidatePath;sha256=(Get-FileHash -LiteralPath $candidatePath -Algorithm SHA256).Hash.ToLowerInvariant();bytes=(Get-Item -LiteralPath $candidatePath).Length}
    scope='Only original Boolean argument expressions were extracted from the candidate AST and evaluated with synthetic dictionaries. This did not execute IdentityGate, NewOwnedApp, broker queries, builder control flow, cleanup, or any COM/CIM access. This is not a runtime ownership or execution approval.'
    originalExpressions=$expressions
    cases=$results
    passed=(@($results | Where-Object {!$_.passed}).Count -eq 0)
    COMExecuted=$false; CIMQueried=$false; cleanupExecuted=$false; builderExecuted=$false; executionApproved=$false
}
$output=Join-Path $reviewRoot 'BROKER_PREDICATE_REVIEW.json'
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($report|ConvertTo-Json -Depth 20)+[char]10)
$stream=[IO.File]::Open($output,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
[ordered]@{path=$output;sha256=(Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant();passed=$report.passed;cases=$cases.Count}|ConvertTo-Json
if(!$report.passed){exit 1}
