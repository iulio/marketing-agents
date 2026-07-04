param(
    [string]$BaseUrl = "http://127.0.0.1:8080",
    [string]$Email = "admin@agency.com",
    [string]$Password = $env:DEFAULT_ADMIN_PASSWORD
)

$ErrorActionPreference = "Stop"

if (-not $Password) {
    throw "Provide -Password or set DEFAULT_ADMIN_PASSWORD."
}

$loginBody = @{
    email = $Email
    password = $Password
} | ConvertTo-Json

$login = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/api/auth/login" `
    -ContentType "application/json" `
    -Body $loginBody

$token = $login.token
if (-not $token) {
    throw "Login did not return a token."
}

$headers = @{ Authorization = "Bearer $token" }
$name = "Smoke Client $(Get-Date -Format yyyyMMddHHmmss)"

$createBody = @{
    name = $name
    industry = "Testing"
    website = "https://example.com"
    billing_email = "billing@example.com"
    platform_status = "pending"
    billing_info = @{ plan = "test" }
    settings = @{ timezone = "UTC" }
} | ConvertTo-Json -Depth 5

$created = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/api/clients" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $createBody

$clientId = $created.client_id
if (-not $clientId) {
    throw "Create client did not return client_id."
}

try {
    $list = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/clients" -Headers $headers
    $client = $list.clients | Where-Object { $_.id -eq $clientId } | Select-Object -First 1
    if (-not $client) {
        throw "Created client not found in list."
    }
    if ($client.platform_status -ne "pending") {
        throw "Expected pending status, got $($client.platform_status)."
    }
    if ($null -eq $client.campaign_count) {
        throw "campaign_count missing from client list."
    }

    $patchBody = @{
        industry = "Updated Testing"
        platform_status = "suspended"
    } | ConvertTo-Json

    $patched = Invoke-RestMethod `
        -Method Patch `
        -Uri "$BaseUrl/api/clients/$clientId" `
        -Headers $headers `
        -ContentType "application/json" `
        -Body $patchBody

    if ($patched.client.platform_status -ne "suspended") {
        throw "Patch endpoint did not update platform_status."
    }

    $statusBody = @{ platform_status = "active" } | ConvertTo-Json
    $status = Invoke-RestMethod `
        -Method Patch `
        -Uri "$BaseUrl/api/clients/$clientId/status" `
        -Headers $headers `
        -ContentType "application/json" `
        -Body $statusBody

    if ($status.platform_status -ne "active") {
        throw "Status endpoint did not return active."
    }
}
finally {
    Invoke-RestMethod `
        -Method Delete `
        -Uri "$BaseUrl/api/clients/$clientId" `
        -Headers $headers | Out-Null
}

[pscustomobject]@{
    login = "ok"
    client_id = $clientId
    client_created = $true
    status_flow = "pending -> suspended -> active"
    deleted = $true
} | ConvertTo-Json