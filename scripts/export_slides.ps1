param(
    [string]$pptxPath,
    [string]$outputFolder
)

try {
    $ppt = New-Object -ComObject PowerPoint.Application
    $pres = $ppt.Presentations.Open((Resolve-Path $pptxPath).Path, 0, 0, 0)
    if (-not (Test-Path $outputFolder)) {
        New-Item -ItemType Directory -Path $outputFolder -Force | Out-Null
    }
    $absOut = (Resolve-Path $outputFolder).Path
    $pres.SaveAs($absOut, 18)
    $pres.Close()
    $ppt.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($ppt) | Out-Null
    Write-Output "SUCCESS"
} catch {
    Write-Error $_.Exception.Message
}
