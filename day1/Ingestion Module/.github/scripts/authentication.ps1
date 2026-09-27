function Get-AzureAccessToken {
	[CmdletBinding()]
	param(
		[Parameter()]
		[ValidateNotNullOrEmpty()]
		[string]$ResourceUrl,

		[Parameter()]
		[ValidateNotNullOrEmpty()]
		[string]$ServiceName = 'Azure service'
	)

	if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
		throw "Azure CLI is required to acquire an $ServiceName access token."
	}

	$accountJson = (& az account show --output json 2>&1 | Out-String).Trim()
	if ($LASTEXITCODE -ne 0) {
		$null = & az login --only-show-errors
		if ($LASTEXITCODE -ne 0) {
			throw 'Azure CLI authentication failed.'
		}
	}

	$tokenJson = (& az account get-access-token --resource $ResourceUrl --output json 2>&1 | Out-String).Trim()
	if ($LASTEXITCODE -ne 0) {
		throw "Unable to acquire an $ServiceName access token."
	}

	try {
		$tokenResponse = $tokenJson | ConvertFrom-Json -ErrorAction Stop
	}
	catch {
		throw 'Azure CLI returned an invalid access-token response.'
	}

	if ([string]::IsNullOrWhiteSpace($tokenResponse.accessToken)) {
		throw 'Azure CLI returned no Fabric access token.'
	}

	return $tokenResponse.accessToken
}

function Get-FabricAccessToken {
	[CmdletBinding()]
	param(
		[Parameter()]
		[ValidateNotNullOrEmpty()]
		[string]$ResourceUrl = 'https://api.fabric.microsoft.com'
	)

	return Get-AzureAccessToken -ResourceUrl $ResourceUrl -ServiceName 'Fabric'
}

function Get-AzureDatabaseAccessToken {
	[CmdletBinding()]
	param(
		[Parameter()]
		[ValidateNotNullOrEmpty()]
		[string]$ResourceUrl = 'https://database.windows.net/'
	)

	return Get-AzureAccessToken -ResourceUrl $ResourceUrl -ServiceName 'Azure Database'
}
