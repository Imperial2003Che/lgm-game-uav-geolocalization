$ErrorActionPreference='Stop'
$W=Split-Path -Parent $MyInvocation.MyCommand.Path
$O=Join-Path $W 'output_v2'
$spec=Get-Content -LiteralPath (Join-Path $W 'CONVERSION_SPEC.json') -Raw | ConvertFrom-Json -DateKind String
$ci=[Globalization.CultureInfo]::InvariantCulture
function Num([double]$v){$v.ToString('R',$ci)}
function Cell($s,[string]$n,[string]$v){$s.CellsU($n).FormulaU=$v}
function Desc([string]$p){$i=Get-Item -LiteralPath $p;[ordered]@{path=$i.FullName;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant();bytes=$i.Length}}
function SaveJson([string]$p,$v){if(Test-Path -LiteralPath $p){throw "Refuse overwrite $p"};[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 100)+"`n",[Text.UTF8Encoding]::new($false))}
function RGBFormula([string]$s){if($s -eq 'white'){return 'RGB(255,255,255)'};if($s -eq 'black'){return 'RGB(0,0,0)'};if($s -match '^#([0-9A-Fa-f]{6})$'){return ('RGB({0},{1},{2})' -f [Convert]::ToInt32($s.Substring(1,2),16),[Convert]::ToInt32($s.Substring(3,2),16),[Convert]::ToInt32($s.Substring(5,2),16))};throw "Unsupported color $s"}
function UserText($s,[string]$n,[string]$v){[void]$s.AddNamedRow(242,$n,0);Cell $s "User.$n" ('"'+$v.Replace('"','""')+'"')}
$initial=@(Get-CimInstance Win32_Process -Filter "Name = 'VISIO.EXE'" | ForEach-Object { [ordered]@{pid=$_.ProcessId;parent=$_.ParentProcessId;utc=$_.CreationDate.ToUniversalTime().ToString('o');ticks=$_.CreationDate.ToUniversalTime().Ticks.ToString();command=$_.CommandLine}})
$events=[Collections.Generic.List[object]]::new();$results=[Collections.Generic.List[object]]::new();$maps=[Collections.Generic.List[object]]::new()
$app=$null;$doc=$null;$owned=$false;$stage='initial';$ok=$false
Add-Type -AssemblyName System.Drawing
$bitmap=[Drawing.Bitmap]::new(1,1);$graphics=[Drawing.Graphics]::FromImage($bitmap);$format=[Drawing.StringFormat]::GenericTypographic.Clone()
function NewOwnedApp([string]$purpose){
 $a=New-Object -ComObject Visio.InvisibleApp
 if(@($initial|Where-Object { $_.pid -eq $a.ProcessID }).Count){throw 'New InvisibleApp unexpectedly shares a preexisting process; refuse use.'}
 $p=Get-CimInstance Win32_Process -Filter ("ProcessId = "+$a.ProcessID)
 $events.Add([ordered]@{event='created';purpose=$purpose;utc=[DateTimeOffset]::UtcNow.ToString('o');pid=$a.ProcessID;parent=$p.ParentProcessId;creationUTC=$p.CreationDate.ToUniversalTime().ToString('o');ticks=$p.CreationDate.ToUniversalTime().Ticks.ToString();command=$p.CommandLine;version=$a.Version;fullBuild=$a.FullBuild;visible=$a.Visible})
 return $a
}
try {
 $stage='create';$app=NewOwnedApp 'author native shapes';$owned=$true
 foreach($f in $spec.figures){
  $stage='build '+$f.dataset;$doc=$app.Documents.Add('');$page=$doc.Pages.Item(1);$page.Name=$f.dataset
  $wi=[double]$f.widthMm/25.4;$hi=[double]$f.heightMm/25.4;$sx=$wi/[double]$f.viewBox[2];$sy=$hi/[double]$f.viewBox[3]
  Cell $page.PageSheet 'PageWidth' ((Num $wi)+' in');Cell $page.PageSheet 'PageHeight' ((Num $hi)+' in')
  Cell $page.PageSheet 'DrawingScale' '1 in';Cell $page.PageSheet 'PageScale' '1 in'
  UserText $page.PageSheet 'Notes' (Get-Content -LiteralPath $f.notes.path -Raw)
  UserText $page.PageSheet 'SourceSVG_SHA256' $f.svg.sha256
  UserText $page.PageSheet 'SourceCSV_SHA256' $f.csv.sha256
  foreach($p in $f.primitives){
   $a=$p.attrs;$shape=$null;$position=$null
   switch($p.tag){
    'rect' {$x=[double]$a.x*$sx;$y=$hi-[double]$a.y*$sy;$ww=[double]$a.width*$sx;$hh=[double]$a.height*$sy;$shape=$page.DrawRectangle($x,($y-$hh),($x+$ww),$y)}
    'line' {$shape=$page.DrawLine(([double]$a.x1*$sx),($hi-[double]$a.y1*$sy),([double]$a.x2*$sx),($hi-[double]$a.y2*$sy))}
    'circle' {$x=[double]$a.cx*$sx;$y=$hi-[double]$a.cy*$sy;$rx=[double]$a.r*$sx;$ry=[double]$a.r*$sy;$shape=$page.DrawOval(($x-$rx),($y-$ry),($x+$rx),($y+$ry))}
    'polygon' {$xy=[Collections.Generic.List[double]]::new();foreach($pair in ($a.points -split '\s+')){if(!$pair){continue};$v=$pair.Split(',');$xy.Add([double]$v[0]*$sx);$xy.Add($hi-[double]$v[1]*$sy)};$xy.Add($xy[0]);$xy.Add($xy[1]);$arr=$xy.ToArray();$shape=$page.DrawPolyline([ref]$arr,0)}
    'text' {
     $size=[double]$a.'font-size';if($size -lt 8){throw 'Font below 8 pt'}
     $style=[Drawing.FontStyle]::Regular;if($a.'font-weight' -eq 'bold'){$style=[Drawing.FontStyle]::Bold}
     $font=[Drawing.Font]::new('Arial',[single]($size*96/72),$style,[Drawing.GraphicsUnit]::Pixel)
     $tw=$graphics.MeasureString([string]$p.text,$font,[Drawing.PointF]::new(0,0),$format).Width/96+2/72;$font.Dispose()
     $x=[double]$a.x*$sx;$baseline=$hi-[double]$a.y*$sy;$left=$x
     if($a.'text-anchor' -eq 'middle'){$left-=$tw/2};if($a.'text-anchor' -eq 'end'){$left-=$tw}
     $th=$size*1.4/72;$bottom=$baseline-$size*.35/72
     $shape=$page.DrawRectangle($left,$bottom,($left+$tw),($bottom+$th));$shape.Text=[string]$p.text
     Cell $shape 'Char.Font' 'FONT("Arial")';Cell $shape 'Char.Size' ((Num $size)+' pt');Cell $shape 'Char.Style' $(if($a.'font-weight' -eq 'bold'){'1'}else{'0'})
     Cell $shape 'Char.Color' (RGBFormula $a.fill);Cell $shape 'Para.HorzAlign' '1';Cell $shape 'VerticalAlign' '1'
     foreach($cell in @('LeftMargin','RightMargin','TopMargin','BottomMargin')){Cell $shape $cell '0 in'}
     Cell $shape 'FillPattern' '0';Cell $shape 'LinePattern' '0';$position=[ordered]@{xAnchorIn=$x;baselineIn=$baseline;leftIn=$left;bottomIn=$bottom;widthIn=$tw;heightIn=$th;fontPt=$size;anchor=$a.'text-anchor'}
    }
    default {throw ('Unsupported tag '+$p.tag)}
   }
   $shape.NameU=$p.name;$shape.Data1=($p.ancestors -join '/');$shape.Data2=$p.tag;$shape.Data3=[string]$p.ordinal
   Cell $shape 'ShdwPattern' '0'
   if($p.tag -ne 'text'){
    if(!$a.fill -or $a.fill -eq 'none'){Cell $shape 'FillPattern' '0'}else{Cell $shape 'FillPattern' '1';Cell $shape 'FillForegnd' (RGBFormula $a.fill)}
    if(!$a.stroke -or $a.stroke -eq 'none'){Cell $shape 'LinePattern' '0'}else{Cell $shape 'LinePattern' '1';Cell $shape 'LineColor' (RGBFormula $a.stroke);Cell $shape 'LineWeight' ((Num ([double]$a.'stroke-width'*$sx))+' in')}
    Cell $shape 'BeginArrow' '0';Cell $shape 'EndArrow' '0'
   }
   $maps.Add([ordered]@{dataset=$f.dataset;ordinal=$p.ordinal;nameU=$shape.NameU;shapeID=$shape.ID;tag=$p.tag;sourceAncestors=$p.ancestors;text=$p.text;textLayout=$position})
  }
  if($page.Shapes.Count -ne $f.expectedShapes){throw 'Shape count mismatch'}
  $dest=Join-Path $O ('formal_main_'+$f.dataset+'_native_editable.vsdx');if(Test-Path -LiteralPath $dest){throw 'Refuse existing VSDX'}
  $doc.SaveAs($dest);$events.Add([ordered]@{event='saved_then_closed';dataset=$f.dataset;utc=[DateTimeOffset]::UtcNow.ToString('o');shapes=$page.Shapes.Count;path=$dest});$doc.Close();$doc=$null
  $results.Add([ordered]@{dataset=$f.dataset;vsdx=(Desc $dest);shapes=$f.expectedShapes;texts=$f.expectedTexts;widthMm=$f.widthMm;heightMm=$f.heightMm;notes=$f.notes})
 }
 $app.Quit();[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app);$app=$null;$owned=$false
 $stage='reopen-export';$app=NewOwnedApp 'reopen saved VSDX and export';$owned=$true
 foreach($r in $results){
  $doc=$app.Documents.OpenEx($r.vsdx.path,2);$page=$doc.Pages.Item(1)
  if($page.Shapes.Count -ne $r.shapes){throw 'Reopened count mismatch'}
  $png=Join-Path $O ('previews/formal_main_'+$r.dataset+'_visio_reopened.png');$pdf=Join-Path $O ('previews/formal_main_'+$r.dataset+'_visio_reopened.pdf')
  if((Test-Path -LiteralPath $png) -or (Test-Path -LiteralPath $pdf)){throw 'Refuse existing preview'}
  $page.Export($png);$doc.ExportAsFixedFormat(1,$pdf,1,0)
  $r['preview']=Desc $png;$r['pdf']=Desc $pdf
  $events.Add([ordered]@{event='reopened_exported_closed';dataset=$r.dataset;utc=[DateTimeOffset]::UtcNow.ToString('o');shapes=$page.Shapes.Count})
  $doc.Close();$doc=$null
 }
 $ok=$true
} catch {
 SaveJson (Join-Path $W 'BUILD_FAILURE.json') ([ordered]@{utc=[DateTimeOffset]::UtcNow.ToString('o');stage=$stage;message=$_.Exception.ToString();scriptStack=$_.ScriptStackTrace;source=(Desc $MyInvocation.MyCommand.Path);events=$events;results=$results})
 throw
} finally {
 if($null -ne $doc -and $owned){$doc.Saved=$true;$doc.Close()}
 if($null -ne $app -and $owned){$ownedPID=$app.ProcessID;$app.Quit();[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app);$events.Add([ordered]@{event='own_instance_quit';pid=$ownedPID;utc=[DateTimeOffset]::UtcNow.ToString('o')})}
 $graphics.Dispose();$bitmap.Dispose();$format.Dispose()
}
if($ok){
 SaveJson (Join-Path $W 'NATIVE_SHAPE_MAP.json') @{shapes=$maps}
 SaveJson (Join-Path $W 'BUILD_REPORT.json') ([ordered]@{schema='native-visio-build.v1';utc=[DateTimeOffset]::UtcNow.ToString('o');passed=$true;source=(Desc $MyInvocation.MyCommand.Path);spec=(Desc (Join-Path $W 'CONVERSION_SPEC.json'));initialVisio=$initial;events=$events;figures=$results;shapeMap=(Desc (Join-Path $W 'NATIVE_SHAPE_MAP.json'));settingsChanged=$false;existingApplicationsTouched=$false;method='Direct native ShapeSheet primitives; no import/embed; fresh invisible instance for reread/export';scientificExecution=$false})
 (Desc (Join-Path $W 'BUILD_REPORT.json'))|ConvertTo-Json
}
