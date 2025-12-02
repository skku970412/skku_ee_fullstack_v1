Param(
    [string]$Port = "COM5",
    [int]$BaudRate = 9600,
    [string]$Message = "START",
    [switch]$NoNewline,
    [float]$DelaySeconds = 0.2
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Log {
    Param([string]$Text)
    Write-Host "[serial-trigger] $Text"
}

try {
    $payload = if ($NoNewline) { $Message } else { "$Message`n" }
    $serial = New-Object System.IO.Ports.SerialPort $Port, $BaudRate, 'None', 8, 'one'
    $serial.DtrEnable = $true
    $serial.RtsEnable = $true
    $serial.Open()
    if ($DelaySeconds -gt 0) {
        Start-Sleep -Seconds $DelaySeconds
    }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
    $serial.Write($bytes, 0, $bytes.Length)
    Write-Log ("Sent '{0}' ({1} bytes) to {2} at {3} baud." -f $payload.TrimEnd(), $bytes.Length, $Port, $BaudRate)
}
catch {
    Write-Error "[serial-trigger] Failed to send: $($_.Exception.Message)"
    exit 1
}
finally {
    if ($null -ne $serial -and $serial.IsOpen) {
        $serial.Close()
    }
}
