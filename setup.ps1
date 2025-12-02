Param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSCommandPath
$VenvPath = Join-Path $Root '.venv'

function Write-SetupLog {
    Param([string]$Message)
    Write-Host "[setup] $Message"
}

function Get-PythonPath {
    foreach ($name in @('python3', 'python')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($null -ne $cmd) {
            return $cmd.Path
        }
    }
    return $null
}

$python = Get-PythonPath

Push-Location $Root
try {
    if ($null -ne $python) {
        if (-not (Test-Path $VenvPath)) {
            Write-SetupLog ".venv 가 존재하지 않아 새로 생성합니다."
            & $python -m venv $VenvPath
        }
        $venvPython = if (Test-Path (Join-Path $VenvPath 'Scripts\python.exe')) {
            Join-Path $VenvPath 'Scripts\python.exe'
        } else {
            Join-Path $VenvPath 'bin/python'
        }

        if (Test-Path $venvPython) {
            if (Test-Path (Join-Path $Root 'backend\requirements.txt')) {
                Write-SetupLog "백엔드 Python 의존성을 설치/업데이트합니다."
                & $venvPython -m pip install --upgrade pip | Out-Null
                & $venvPython -m pip install -r (Join-Path $Root 'backend\requirements.txt')
            }
        } else {
            Write-Warning "[setup] .venv 내에서 python 실행 파일을 찾지 못했습니다."
        }
    } else {
        Write-Warning "[setup] python3 / python 명령을 찾을 수 없어 .venv 생성을 건너뜁니다."
    }

    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if ($null -eq $npm) {
        Write-Warning "[setup] npm 명령을 찾을 수 없어 프론트엔드 의존성 설치를 생략합니다."
        return
    }

    foreach ($project in @('admin-front', 'user-front')) {
        $projPath = Join-Path $Root $project
        $packageJson = Join-Path $projPath 'package.json'
        if (-not (Test-Path $packageJson)) {
            Write-Warning "[setup] $project/package.json 을 찾을 수 없어 건너뜁니다."
            continue
        }

        if (Test-Path (Join-Path $projPath 'node_modules')) {
            continue
        }

        Write-SetupLog "$project 의존성을 설치합니다."
        Push-Location $projPath
        try {
            & $npm.Path install
        } finally {
            Pop-Location
        }
    }

    Write-SetupLog "준비가 완료되었습니다."
} finally {
    Pop-Location
}
