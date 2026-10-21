$ErrorActionPreference = 'Continue'
$Dest = 'F:\Kho-anh'
$Ext  = '.jpg','.jpeg','.png','.heic','.webp','.tif','.tiff','.bmp','.gif'
$MinSize = 40kb

# label = nhan thu muc con trong kho; cat = phan loai; excl = wildcard loai tru
$Sources = @(
  @{cat='01_May-rang';      label='Photo';             path='F:\Photo';                                                  excl=@('*\Probat\*')},
  @{cat='01_May-rang';      label='CV-Anh';            path='F:\CV\Anh';                                                 excl=@()},
  @{cat='01_May-rang';      label='Otesla-auto';       path='F:\Otesla_coffee_roaster_auto\Hinh-anh';                    excl=@()},
  @{cat='02_Vat-tu';        label='Vat-tu-Otesla';     path='F:\Vat-tu-Otesla';                                          excl=@('*\22_User_manual\*')},
  @{cat='02_Vat-tu';        label='Catalog-30KG-SILO'; path='F:\Project\112_Quanly\113_30KG_SILO\03_Catalog';            excl=@()},
  @{cat='03_Logo';          label='HMI-Logo';          path='F:\HMI\Logo';                                               excl=@()},
  @{cat='03_Logo';          label='HMI-Gif-Logo';      path='F:\HMI\Gif\Manual logo';                                    excl=@()},
  @{cat='04_Icon-HMI';      label='HMI-Icon-bank';     path='F:\HMI\Icon bank';                                          excl=@()},
  @{cat='04_Icon-HMI';      label='HMI-man-hinh';      path='F:\HMI\3XILANH_NOLOADCELL\HMI_3XILANH_NOLOADCELL_23_02_2020\Thanh\11_2026'; excl=@()},
  @{cat='04_Icon-HMI';      label='hmi-bitmap-repo';   path='F:\Project\100_OTL_06ALS - CMS - Cacao\assets\hmi-bitmap';  excl=@()},
  @{cat='05_Manual';        label='User-manual';       path='F:\Vat-tu-Otesla\22_User_manual';                           excl=@()},
  @{cat='05_Manual';        label='File-Manual';       path='F:\File-Manual';                                            excl=@()},
  @{cat='05_Manual';        label='Manual-AI';         path='F:\Project\112_Quanly\122_Manual_AI';                       excl=@('*\build\*','*\.git\*','*\node_modules\*')},
  @{cat='05_Manual';        label='CV-Huong-dan';      path='F:\CV\Huong-dan';                                           excl=@()},
  @{cat='06_Banner-social'; label='Banner-TruyenThong';path='F:\Project\112_Quanly\118_Banner_TruyenThong';              excl=@('*\_soi\*','*\tex\*','*\.git\*','*\node_modules\*')},
  @{cat='07_Render-3D';     label='Inventor-3D';       path='F:\Project\112_Quanly\121_Inventor_3D';                     excl=@('*\.git\*','*\node_modules\*')},
  @{cat='08_Catalog-Probat';label='Probat-agents';     path='F:\Probat\Information for agents';                          excl=@()},
  @{cat='08_Catalog-Probat';label='Photo-Probat';      path='F:\Photo\Probat';                                           excl=@()}
)

# F:\File-AI: dinh tuyen theo tu khoa ten thu muc
function Get-FileAICat($rel) {
  if ($rel -match '(?i)logo|mark_otesla|sticker|chu_ky|_ava')               { return '03_Logo' }
  if ($rel -match '(?i)icon|hmi')                                           { return '04_Icon-HMI' }
  if ($rel -match '(?i)banner|post|catalog|cover|quick_manual|user-manual') { return '06_Banner-social' }
  return '09_Thiet-ke-khac'
}

$seen  = @{}
$index = New-Object System.Collections.ArrayList
$script:nCopy = 0; $script:nDup = 0; $script:nErr = 0

function Add-Img($src, $cat, $label, $rel) {
  try { $h = (Get-FileHash -LiteralPath $src.FullName -Algorithm MD5 -ErrorAction Stop).Hash } catch { $script:nErr++; return }
  if ($seen.ContainsKey($h)) { $script:nDup++; return }
  $target = Join-Path $Dest (Join-Path $cat (Join-Path $label $rel))
  $dir = Split-Path $target -Parent
  if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  try {
    Copy-Item -LiteralPath $src.FullName -Destination $target -Force -ErrorAction Stop
    $seen[$h] = $target
    $script:nCopy++
    [void]$index.Add([pscustomobject]@{
      Kho   = $target.Substring($Dest.Length+1)
      Nguon = $src.FullName
      KB    = [math]::Round($src.Length/1kb)
      Ngay  = $src.LastWriteTime.ToString('yyyy-MM-dd')
      MD5   = $h
    })
  } catch { $script:nErr++ }
}

function Test-Excluded($full, $pats) {
  foreach ($p in $pats) { if ($full -like $p) { return $true } }
  return $false
}

foreach ($s in $Sources) {
  if (-not (Test-Path -LiteralPath $s.path)) { Write-Host "BO QUA (khong co): $($s.path)"; continue }
  $files = @(Get-ChildItem -LiteralPath $s.path -Recurse -File -Force -ErrorAction SilentlyContinue |
             Where-Object { $Ext -contains $_.Extension.ToLower() -and $_.Length -ge $MinSize -and -not (Test-Excluded $_.FullName $s.excl) })
  foreach ($f in $files) {
    $rel = $f.FullName.Substring($s.path.Length).TrimStart('\')
    Add-Img $f $s.cat $s.label $rel
  }
  Write-Host ("{0,-22} -> {1,-18} {2,5} anh" -f $s.label, $s.cat, $files.Count)
}

$root = 'F:\File-AI'
$fa = @(Get-ChildItem -LiteralPath $root -Recurse -File -Force -ErrorAction SilentlyContinue |
        Where-Object { $Ext -contains $_.Extension.ToLower() -and $_.Length -ge $MinSize })
foreach ($f in $fa) {
  $rel = $f.FullName.Substring($root.Length).TrimStart('\')
  Add-Img $f (Get-FileAICat $rel) 'File-AI' $rel
}
Write-Host ("{0,-22} -> {1,-18} {2,5} anh" -f 'File-AI', '(phan loai)', $fa.Count)

New-Item -ItemType Directory -Path (Join-Path $Dest '99_Xuat-Photoshop') -Force | Out-Null
$index | Sort-Object Kho | Export-Csv -LiteralPath (Join-Path $Dest '_index.csv') -NoTypeInformation -Encoding UTF8

Write-Host ''
Write-Host '=== XONG ==='
Write-Host "Da chep          : $script:nCopy anh"
Write-Host "Trung lap bo qua : $script:nDup"
Write-Host "Loi              : $script:nErr"
$tot = (Get-ChildItem -LiteralPath $Dest -Recurse -File | Measure-Object Length -Sum).Sum/1GB
Write-Host ("Dung luong kho   : {0:N2} GB" -f $tot)
