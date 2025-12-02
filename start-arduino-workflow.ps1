Param(
    [string]$Port = "COM5",
    [int]$BaudRate = 9600,
    [string]$WakeMessage = "START",
    [string]$TargetValue = "1",
    [string]$Plate = "",
    [float]$DelaySeconds = 5.0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Log {
    Param([string]$Text)
    Write-Host "[arduino] $Text"
}

$serial = $null

try {
    $serial = New-Object System.IO.Ports.SerialPort($Port, $BaudRate, 'None', 8, 'one')
    $serial.NewLine = "`n"
    $serial.ReadTimeout = 200
    $serial.DtrEnable = $true
    $serial.RtsEnable = $true
    $serial.Open()

    function Send-SerialLine {
        Param([string]$Message)
        $payload = "$Message`n"
        $serial.Write($payload)
        Write-Log ("Sent '{0}' to {1}" -f $Message, $serial.PortName)
    }

    Send-SerialLine -Message $WakeMessage
    if ($DelaySeconds -gt 0) {
        Start-Sleep -Seconds $DelaySeconds
    }

    if ($Plate) {
        Send-SerialLine -Message ("PLATE:{0}" -f $Plate)
        if ($DelaySeconds -gt 0) {
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    Send-SerialLine -Message ("TARGET:{0}" -f $TargetValue)
    if ($DelaySeconds -gt 0) {
        Start-Sleep -Seconds $DelaySeconds
    }

    Write-Log "Listening for serial output... (Press Enter to stop)"
    while ($true) {
        try {
            $incoming = $serial.ReadExisting()
            if ($incoming) {
                foreach ($line in $incoming -split "(`r`n|`n)") {
                    if (-not [string]::IsNullOrWhiteSpace($line)) {
                        Write-Log ("Serial >> {0}" -f $line.Trim())
                    }
                }
            }
        } catch [System.TimeoutException] {
            # Ignore read timeouts
        }
        $keyCheck = $false
        try {
            $keyCheck = [Console]::KeyAvailable
        } catch [System.InvalidOperationException] {
            # Non-interactive host; ignore key checks.
            $keyCheck = $false
        }
        if ($keyCheck) {
            $key = [Console]::ReadKey($true)
            if ($key.Key -eq [ConsoleKey]::Enter) {
                Write-Log "Stop requested. Closing serial connection."
                break
            }
        }
        Start-Sleep -Milliseconds 100
    }
}
finally {
    if ($null -ne $serial -and $serial.IsOpen) {
        $serial.Close()
    }
}
