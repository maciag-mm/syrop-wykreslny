# Syrop Wykreslny - budowanie programu dla Windows:
#   exe (PyInstaller, folder) + instalator (Inno Setup) + wersja przenosna ZIP.
# Potrzebny tylko internet; Python, PyInstaller i Inno Setup pobierane sa automatycznie
# do %LOCALAPPDATA%\SyropWykreslny-build (nie zmienia to niczego w systemie).
# Uruchomienie: kliknij BUDUJ.bat (albo: powershell -ExecutionPolicy Bypass -File build.ps1)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Build = Split-Path -Parent $MyInvocation.MyCommand.Path
$Proj  = Split-Path -Parent $Build
$Src   = Join-Path $Proj 'src\syrop_wykreslny.py'
$Out   = Join-Path $Proj 'wynik'
$Work  = Join-Path $env:LOCALAPPDATA 'SyropWykreslny-build'
$Ver   = '1.06'
$PyVer = '3.12'
New-Item -ItemType Directory -Force -Path $Work, $Out | Out-Null
$Log = Join-Path $Out 'budowanie.log'
Start-Transcript -Path $Log -Force | Out-Null

function Step($t) { Write-Host ''; Write-Host "=== $t ===" -ForegroundColor Cyan }
function Run($exe, [string[]]$a) {
    $ErrorActionPreference = 'Continue'
    & $exe @a
    if ($LASTEXITCODE -ne 0) { throw "Polecenie nie powiodlo sie ($LASTEXITCODE): $exe $($a -join ' ')" }
}

try {
    # --- 1. uv (menedzer Pythona i pakietow)
    Step '1/7  Menedzer pakietow uv'
    $uv = Join-Path $Work 'uv\uv.exe'
    if (-not (Test-Path $uv)) {
        $zip = Join-Path $Work 'uv.zip'
        Invoke-WebRequest 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip' -OutFile $zip -UseBasicParsing
        Expand-Archive $zip -DestinationPath (Join-Path $Work 'uv') -Force
        Remove-Item $zip
    }
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $Work 'python'
    $env:UV_CACHE_DIR = Join-Path $Work 'cache'

    # --- 2. Python + srodowisko
    Step "2/7  Python $PyVer (tylko do budowania)"
    $venv = Join-Path $Work 'venv'
    $py = Join-Path $venv 'Scripts\python.exe'
    if (-not (Test-Path $py)) { Run $uv @('venv', $venv, '--python', $PyVer, '--python-preference', 'only-managed') }

    # --- 3. Pakiety
    Step '3/7  Pakiety: PyQt6, GDAL, GeographicLib, PyInstaller'
    Run $uv @('pip', 'install', '--python', $py, '--upgrade', 'pyqt6', 'pyinstaller', 'geographiclib', 'pillow', 'ezdxf')
    function Test-Gdal { $ErrorActionPreference = 'Continue'; & $py -c "from osgeo import gdal, ogr, osr" 2>&1 | Out-Null; return ($LASTEXITCODE -eq 0) }
    if (-not (Test-Gdal)) {
        $ErrorActionPreference = 'Continue'
        & $uv pip install --python $py --only-binary ':all:' gdal 2>&1 | Out-Host
        $ErrorActionPreference = 'Stop'
        if (-not (Test-Gdal)) {
            Write-Host 'GDAL z PyPI niedostepny w wersji binarnej - pobieram kolo z cgohlke/geospatial-wheels'
            $rel = Invoke-RestMethod 'https://api.github.com/repos/cgohlke/geospatial-wheels/releases/latest' -UseBasicParsing
            $tag = 'cp' + $PyVer.Replace('.', '')
            $asset = $rel.assets | Where-Object { $_.name -match "^gdal-.*-$tag-$tag-win_amd64\.whl$" } | Select-Object -First 1
            if (-not $asset) { throw "Nie znaleziono pliku GDAL dla $tag w wydaniu $($rel.tag_name)" }
            $whl = Join-Path $Work $asset.name
            Invoke-WebRequest $asset.browser_download_url -OutFile $whl -UseBasicParsing
            Run $uv @('pip', 'install', '--python', $py, $whl)
        }
    }
    Run $py @('-c', "from osgeo import gdal; print('GDAL', gdal.__version__)")

    # --- 3b. LibreDWG (konwerter DWG <-> DXF dolaczany do programu, licencja GPL-3)
    Step '3b/7 LibreDWG'
    $ldwg = Join-Path $Work 'libredwg'
    if (-not (Test-Path (Join-Path $ldwg 'dwg2dxf.exe'))) {
        $rel = Invoke-RestMethod 'https://api.github.com/repos/LibreDWG/libredwg/releases/latest' -UseBasicParsing
        $asset = $rel.assets | Where-Object { $_.name -match 'win64.*\.zip$' } | Select-Object -First 1
        if (-not $asset) {
            $rels = Invoke-RestMethod 'https://api.github.com/repos/LibreDWG/libredwg/releases?per_page=15' -UseBasicParsing
            $asset = $rels | ForEach-Object { $_.assets } | Where-Object { $_.name -match 'win64.*\.zip$' } | Select-Object -First 1
        }
        if (-not $asset) { throw 'Nie znaleziono paczki LibreDWG dla Windows 64-bit.' }
        Write-Host "Pobieram $($asset.browser_download_url)"
        $lz = Join-Path $Work $asset.name
        Invoke-WebRequest $asset.browser_download_url -OutFile $lz -UseBasicParsing
        $raw = Join-Path $Work 'libredwg_raw'
        if (Test-Path $raw) { Remove-Item $raw -Recurse -Force }
        Expand-Archive $lz -DestinationPath $raw -Force
        $tool = Get-ChildItem $raw -Recurse -Filter 'dwg2dxf.exe' | Select-Object -First 1
        if (-not $tool) { throw 'W paczce LibreDWG brak dwg2dxf.exe' }
        New-Item -ItemType Directory -Force -Path $ldwg | Out-Null
        Get-ChildItem $tool.DirectoryName -File | Where-Object { $_.Extension -eq '.dll' -or $_.Name -in @('dwg2dxf.exe', 'dxf2dwg.exe') } |
            Copy-Item -Destination $ldwg -Force
        $lic = Get-ChildItem $raw -Recurse -File | Where-Object { $_.Name -match '^(COPYING|LICENSE)' } | Select-Object -First 1
        if ($lic) { Copy-Item $lic.FullName (Join-Path $ldwg 'COPYING.txt') -Force }
        Set-Content (Join-Path $ldwg 'CZYTAJ.txt') -Encoding UTF8 -Value @(
            "LibreDWG $($rel.tag_name) - konwerter DWG <-> DXF uzywany przez Syrop Wykreslny.",
            'Licencja: GNU GPL v3 (plik COPYING.txt). Kod zrodlowy: https://github.com/LibreDWG/libredwg',
            'Program Syrop Wykreslny uruchamia go jako osobny program (dwg2dxf.exe / dxf2dwg.exe).')
    }
    Get-ChildItem $ldwg | Format-Table Name, Length -AutoSize | Out-String | Write-Host
    $env:SYROP_LIBREDWG = $ldwg

    # --- 4. Test przed spakowaniem
    Step '4/7  Test programu (Python)'
    $t1 = Join-Path $Work 'test_py'
    Run $py @($Src, '--selftest', $t1)
    Get-Content (Join-Path $t1 'selftest.txt') -Encoding UTF8 | Write-Host

    # --- 5. PyInstaller
    Step '5/7  Budowanie exe (PyInstaller)'
    $dist = Join-Path $Work 'dist'
    Run $py @('-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
        '--name', 'SyropWykreslny',
        '--icon', (Join-Path $Build 'syrop.ico'),
        '--version-file', (Join-Path $Build 'version_info.txt'),
        '--collect-all', 'osgeo',
        '--collect-submodules', 'geographiclib',
        '--collect-submodules', 'ezdxf', '--collect-data', 'ezdxf',
        '--add-data', "$ldwg;libredwg",
        '--exclude-module', 'tkinter', '--exclude-module', 'matplotlib', '--exclude-module', 'PIL',
        '--distpath', $dist, '--workpath', (Join-Path $Work 'pyi'), '--specpath', $Work,
        $Src)
    $app = Join-Path $dist 'SyropWykreslny'
    $exe = Join-Path $app 'SyropWykreslny.exe'

    Step '     Odchudzanie (usuwanie zbednych plikow)'
    $int = Join-Path $app '_internal'
    $before = (Get-ChildItem $app -Recurse -File | Measure-Object Length -Sum).Sum
    if (Test-Path (Join-Path $int 'libredwg\libredwg-0.dll')) { Remove-Item (Join-Path $int 'libredwg-0.dll') -ErrorAction SilentlyContinue }
    $qt = Join-Path $int 'PyQt6\Qt6'
    @('bin\opengl32sw.dll', 'bin\Qt6Pdf.dll', 'bin\Qt6Network.dll', 'translations',
      'plugins\imageformats\qpdf.dll', 'plugins\tls', 'plugins\networkinformation', 'plugins\generic') |
        ForEach-Object { Remove-Item (Join-Path $qt $_) -Recurse -Force -ErrorAction SilentlyContinue }
    Get-ChildItem (Join-Path $int 'PyQt6') -Filter 'QtNetwork*.pyd' | Remove-Item -Force -ErrorAction SilentlyContinue
    Get-ChildItem (Join-Path $int 'osgeo') -Filter '*.exe' | Remove-Item -Force
    Remove-Item (Join-Path $int 'osgeo\gdal.lib') -ErrorAction SilentlyContinue
    $after = (Get-ChildItem $app -Recurse -File | Measure-Object Length -Sum).Sum
    Write-Host ("Rozmiar programu: {0:N0} MB -> {1:N0} MB" -f ($before / 1MB), ($after / 1MB))

    Step '     Licencje (GPL-3.0 programu i licencje komponentow)'
    $lic = Join-Path $app 'licencje'
    New-Item -ItemType Directory -Force -Path $lic | Out-Null
    Copy-Item (Join-Path $Proj 'LICENSE') (Join-Path $lic 'LICENSE-GPL-3.0.txt') -Force
    Copy-Item (Join-Path $Proj 'THIRD_PARTY_LICENSES.md') $lic -Force
    Copy-Item (Join-Path $Proj 'licenses\*') $lic -Force
    Copy-Item (Join-Path $Proj 'LICENSE') (Join-Path $int 'libredwg\COPYING.txt') -Force
    $site = Join-Path $venv 'Lib\site-packages'
    $bundled = '^(pyqt6|pyqt6_qt6|pyqt6_sip|gdal|numpy|ezdxf|fonttools|pyparsing|typing_extensions|geographiclib|pyinstaller)-'
    Get-ChildItem $site -Directory -Filter '*.dist-info' | Where-Object { $_.Name -match $bundled } | ForEach-Object {
        $files = Get-ChildItem $_.FullName -Recurse -File | Where-Object { $_.Name -match '^(LICEN[CS]E|COPYING|NOTICE|AUTHORS)' }
        if ($files) {
            $d = Join-Path $lic ('python\' + ($_.Name -replace '\.dist-info$', ''))
            New-Item -ItemType Directory -Force -Path $d | Out-Null
            $files | Copy-Item -Destination $d -Force
        }
    }
    $pyLic = Get-ChildItem (Join-Path $Work 'python') -Recurse -File -Filter 'LICENSE.txt' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pyLic) { Copy-Item $pyLic.FullName (Join-Path $lic 'python\LICENSE-Python.txt') -Force }

    Step '     Test spakowanego exe'
    $t2 = Join-Path $Work 'test_exe'
    $env:PROJ_DATA = $null; $env:PROJ_LIB = $null; $env:GDAL_DATA = $null; $env:SYROP_LIBREDWG = $null
    $p = Start-Process -FilePath $exe -ArgumentList @('--selftest', "`"$t2`"") -Wait -PassThru
    Get-Content (Join-Path $t2 'selftest.txt') -Encoding UTF8 | Write-Host
    if ($p.ExitCode -ne 0) { throw 'Test spakowanego exe zakonczyl sie bledem (szczegoly powyzej).' }
    Copy-Item (Join-Path $t2 'selftest.txt') (Join-Path $Out 'test_programu.txt') -Force

    # --- 6. Inno Setup -> instalator
    Step '6/7  Instalator (Inno Setup)'
    $iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
              "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", (Join-Path $Work 'inno\ISCC.exe')) |
            Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $iscc) {
        $is = Join-Path $Work 'innosetup.exe'
        $isUrl = 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe'
        try {
            $page = (Invoke-WebRequest 'https://jrsoftware.org/isdl.php' -UseBasicParsing).Content
            $m = [regex]::Match($page, 'https://[^"]+/innosetup-6\.[0-9.]+\.exe')
            if ($m.Success) { $isUrl = $m.Value }
        } catch { }
        Write-Host "Pobieram $isUrl"
        Invoke-WebRequest $isUrl -OutFile $is -UseBasicParsing
        $p = Start-Process -FilePath $is -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
            '/CURRENTUSER', '/NOICONS', "/DIR=`"$(Join-Path $Work 'inno')`"") -Wait -PassThru
        $iscc = Join-Path $Work 'inno\ISCC.exe'
        if (-not (Test-Path $iscc)) { throw 'Nie udalo sie zainstalowac Inno Setup.' }
    }
    Push-Location $Build
    Run $iscc @('/Q', "/DSourceDir=$app", "/DOutDir=$Out", 'installer.iss')
    Pop-Location

    # --- 7. Wersja przenosna
    Step '7/7  Wersja przenosna (ZIP)'
    $zipOut = Join-Path $Out "SyropWykreslny_${Ver}_przenosny.zip"
    if (Test-Path $zipOut) { Remove-Item $zipOut }
    Compress-Archive -Path $app -DestinationPath $zipOut -CompressionLevel Optimal

    Step '     Test wersji przenosnej w folderze z polskimi znakami'
    $pl = Join-Path $Work ('test Pr' + [char]0x00F3 + 'ba ' + [char]0x0105 + [char]0x0119 + [char]0x0142 + [char]0x015B + [char]0x017C)
    if (Test-Path $pl) { Remove-Item $pl -Recurse -Force }
    Expand-Archive $zipOut -DestinationPath $pl -Force
    $t3 = Join-Path $pl 'wyniki testu'
    $p = Start-Process -FilePath (Join-Path $pl 'SyropWykreslny\SyropWykreslny.exe') -ArgumentList @('--selftest', "`"$t3`"") -Wait -PassThru
    Get-Content (Join-Path $t3 'selftest.txt') -Encoding UTF8 | Write-Host
    if ($p.ExitCode -ne 0) { throw 'Test wersji przenosnej (polskie znaki w sciezce) zakonczyl sie bledem.' }
    Copy-Item (Join-Path $t3 'selftest.txt') (Join-Path $Out 'test_programu_polskie_znaki.txt') -Force

    Step '     Paczka do przekazania (ZIP)'
    $pk = Join-Path $Work 'paczka'
    if (Test-Path $pk) { Remove-Item $pk -Recurse -Force }
    $top = Join-Path $pk "Syrop Wykreslny $Ver"
    New-Item -ItemType Directory -Force -Path (Join-Path $top 'Wersja bez instalacji') | Out-Null
    Copy-Item (Join-Path $Out "SyropWykreslny_${Ver}_instalator.exe") $top
    Copy-Item $app (Join-Path $top 'Wersja bez instalacji') -Recurse
    Copy-Item (Join-Path $Build 'CZYTAJ.txt') $top
    $final = Join-Path $Out "Syrop_Wykreslny_${Ver}.zip"
    if (Test-Path $final) { Remove-Item $final }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($pk, $final, [System.IO.Compression.CompressionLevel]::Optimal, $false)

    Step '     Kody zrodlowe komponentow GPL (do dolaczenia do wydania na GitHubie)'
    $srcDir = Join-Path $Out 'zrodla_GPL'
    New-Item -ItemType Directory -Force -Path $srcDir | Out-Null
    try {
        $lrel = Invoke-RestMethod 'https://api.github.com/repos/LibreDWG/libredwg/releases/latest' -UseBasicParsing
        $la = $lrel.assets | Where-Object { $_.name -match '^libredwg-[0-9.]+\.tar\.(xz|gz)$' } | Select-Object -First 1
        if ($la) { Invoke-WebRequest $la.browser_download_url -OutFile (Join-Path $srcDir $la.name) -UseBasicParsing; Write-Host "  $($la.name)" }
    } catch { Write-Host "  (nie udalo sie pobrac zrodel LibreDWG: $_)" -ForegroundColor Yellow }
    try {
        $qv = (& $py -c "import importlib.metadata as m; print(m.version('PyQt6'))").Trim()
        $pj = Invoke-RestMethod "https://pypi.org/pypi/PyQt6/$qv/json" -UseBasicParsing
        $sd = $pj.urls | Where-Object { $_.packagetype -eq 'sdist' } | Select-Object -First 1
        if ($sd) { Invoke-WebRequest $sd.url -OutFile (Join-Path $srcDir $sd.filename) -UseBasicParsing; Write-Host "  $($sd.filename)" }
    } catch { Write-Host "  (nie udalo sie pobrac zrodel PyQt6: $_)" -ForegroundColor Yellow }

    Step 'GOTOWE'
    Get-ChildItem $Out | Format-Table Name, @{n = 'MB'; e = { [math]::Round($_.Length / 1MB, 1) } } -AutoSize | Out-String | Write-Host
    Write-Host "Pliki sa w: $Out" -ForegroundColor Green
    Set-Content -Path (Join-Path $Out 'STATUS.txt') -Value 'OK' -Encoding ASCII
}
catch {
    Write-Host ''
    Write-Host "BLAD: $_" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace
    Set-Content -Path (Join-Path $Out 'STATUS.txt') -Value "BLAD: $_" -Encoding UTF8
    exit 1
}
finally {
    Stop-Transcript | Out-Null
}
