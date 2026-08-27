param(
    [string]$BaseUrl = 'http://127.0.0.1:8000'
)

Invoke-RestMethod -Uri "$BaseUrl/api/ready" -Method Get | ConvertTo-Json -Depth 10
