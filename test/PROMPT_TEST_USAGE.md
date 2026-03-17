# Prompt Test Data Usage

This folder provides prompt-focused test data for the AI generation endpoints.

## Files

1. LESSON_PROMPT_TEST_CASES_20.json
2. EXERCISE_PROMPT_TEST_CASES_20.json

## Target APIs

1. POST /api/lesson/generate
2. POST /api/exercise/generate

## Minimal run flow

1. Login and get JWT token.
2. Iterate each case payload and call target API.
3. Compare response status and content with expected section.

## PowerShell quick example

```powershell
$token = "<YOUR_JWT>"
$suite = Get-Content test/LESSON_PROMPT_TEST_CASES_20.json -Raw | ConvertFrom-Json
$headers = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }

foreach ($c in $suite.cases) {
  $body = $c.payload | ConvertTo-Json -Depth 10
  try {
    $resp = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/api/lesson/generate" -Headers $headers -Body $body
    Write-Output ("{0} => OK" -f $c.case_id)
  } catch {
    Write-Output ("{0} => FAIL: {1}" -f $c.case_id, $_.Exception.Message)
  }
}
```

## Notes

1. Some cases are intentionally negative/boundary to verify robustness.
2. Exercise case E019 is expected to fail (types shape mismatch) under current backend implementation.
3. Adjust expected HTTP status if backend validation logic changes.
