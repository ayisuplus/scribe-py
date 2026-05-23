Get-ChildItem -Path "E:\agents factory\writing-agents\scribe-py" -Recurse -Include *.py | ForEach-Object {
    if ($_.DirectoryName -notmatch '__pycache__') {
        $result = python -m py_compile $_.FullName 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "FAIL: $($_.FullName)"
            Write-Host $result
        } else {
            Write-Host "OK: $($_.Name)"
        }
    }
}