# คู่มือ Build GKThai ตั้งแต่เริ่มจนได้ไฟล์ม็อด

คู่มือนี้สร้างแพ็ก `GKThai` จาก source โดยอ่าน reference และ `resources.assets` จากเกมที่ผู้พัฒนาเป็นเจ้าของ กระบวนการ build ไม่เขียนทับไฟล์ใน `Graveyard Keeper_Data`

## 1. สิ่งที่ต้องมี

- Windows 10/11 x64
- Graveyard Keeper ภาคแรกบน Steam รุ่น `1.407`
- BepInEx `5.4.23.5` x64 สำหรับ Unity Mono ติดตั้งในรากเกม
- Git, PowerShell 5.1 ขึ้นไป และ Python 3.11 ขึ้นไป
- `font.ttf` ของแพ็ก GKThai รุ่นเดียวกัน ดาวน์โหลดจากแพ็กพร้อมใช้บน Nexus Mods หรือใช้ฟอนต์ที่มีสิทธิ์ใช้งานของตนเองแล้วอัปเดต config/hash

ตัวอย่างในคู่มือใช้รากเกม:

```text
E:\SteamLibrary\steamapps\common\Graveyard Keeper
```

## 2. เตรียมเกมและ BepInEx

1. ใน Steam เลือก **Properties → Installed Files → Verify integrity of game files** หากเคยใช้แพ็กที่แก้ game assets/DLL
2. แตก BepInEx x64 ลงรากเกม ให้ `winhttp.dll` อยู่ข้าง `Graveyard Keeper.exe`
3. เปิดเกมหนึ่งครั้งแล้วปิด เพื่อให้ BepInEx สร้างโฟลเดอร์
4. ตรวจว่ามี `BepInEx/core/BepInEx.dll` และ `BepInEx/core/0Harmony.dll`

Build ปัจจุบันรองรับ hash ต่อไปนี้เท่านั้น:

| ไฟล์ | SHA-256 |
|---|---|
| `Graveyard Keeper_Data/resources.assets` | `215c7981901a4b72d5db717666ba47ad3cc032527c95f58dc39d8af1293a69ca` |
| `Graveyard Keeper_Data/Managed/Assembly-CSharp-firstpass.dll` | `9dc6def3b7715dd27eeb168ddc0af47e31c6f38d3fbee24bf592899392026498` |
| `Graveyard Keeper_Data/Managed/Assembly-CSharp.dll` | `e72e4270e4b88dd0a87ca23c9cf1750aec4c4a0fedb40b6d2dae7902fc9c7fd8` |

ตรวจด้วย PowerShell:

```powershell
$GameRoot = 'E:\SteamLibrary\steamapps\common\Graveyard Keeper'
Get-FileHash -Algorithm SHA256 -LiteralPath `
  "$GameRoot\Graveyard Keeper_Data\resources.assets", `
  "$GameRoot\Graveyard Keeper_Data\Managed\Assembly-CSharp-firstpass.dll", `
  "$GameRoot\Graveyard Keeper_Data\Managed\Assembly-CSharp.dll"
```

ถ้า hash ไม่ตรง ให้หยุดและตรวจรุ่นเกม ห้ามแก้ค่าคงที่เพื่อข้าม BuildGuard โดยยังไม่ได้วิเคราะห์ assembly รุ่นใหม่

## 3. Clone source และสร้าง Python environment

แนะนำให้ clone ใต้ `mods/GKThai` ในรากเกม เพื่อใช้ค่า path อัตโนมัติ:

```powershell
Set-Location $GameRoot
New-Item -ItemType Directory -Force mods | Out-Null
git clone https://github.com/Jakkrich/graveyardkeeper-bepinex-thai-plugin.git mods/GKThai
Set-Location mods/GKThai

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

หาก clone ไว้ที่อื่น ให้ส่ง `-GameRoot` หรือ `--game-root` ทุกคำสั่งที่เกี่ยวข้องกับเกม

## 4. เตรียมฟอนต์ local

Repository ไม่แจก `font.ttf` ให้สร้าง `.local` แล้วคัดลอกฟอนต์จากแพ็ก GKThai บน Nexus Mods:

```powershell
New-Item -ItemType Directory -Force .local | Out-Null
Copy-Item 'D:\Downloads\GKThai\BepInEx\plugins\GKThai\font.ttf' '.local\font.ttf'
Get-FileHash -Algorithm SHA256 -LiteralPath '.local\font.ttf'
```

สำหรับ build ที่ตรงกับ `0.1.0` ต้องได้:

```text
98560a50f5c6430f8e6570fd315a0bf056470eb72e7fb812148f17fcfec4dd57
```

หากใช้ฟอนต์อื่น ต้องมีอักขระที่คำแปลใช้ทั้งหมด แก้ `config/gk1-font.json` ให้ `font_sha256` ตรง แล้ว build payload และ DLL ใหม่พร้อมกัน การเปลี่ยนเฉพาะ `font.ttf` หลัง build ใช้ไม่ได้

## 5. Export ภาษาอังกฤษและแก้คำแปล

ขั้นตอน export เป็นตัวเลือกสำหรับตรวจ key/source จากเกมที่ติดตั้ง:

```powershell
python tools/export_source.py --game-root $GameRoot
```

ผลลัพธ์อยู่ที่ `.local/source_en.csv` และไม่ถูก commit ไฟล์คำแปลหลักคือ `translations/th.csv`:

```csv
key,source,translation
Loading prompt,Loading...,กำลังโหลด...
```

กติกา:

- บันทึกเป็น UTF-8
- ห้ามแก้ `key` และ `source`
- รักษา `%1`, ตัวเลข, newline, `[token]`, `{token}`, `<markup>` และ icon token ให้ครบ
- ใช้ Unicode ไทยตามปกติ ห้ามใส่ PUA `U+E000–U+F8FF`

Payload builder จะเทียบ key/source กับ locale English ใน `resources.assets` ก่อน build

## 6. รัน unit tests

```powershell
python -m unittest discover -s tests
powershell -ExecutionPolicy Bypass -File tests/run-runtime-tests.ps1
```

รอบแรกที่ยังไม่มี `payload/` integration test ของ payload จริงจะถูก skip หนึ่งรายการ จากนั้นให้รันอีกครั้งหลังขั้นตอน build

## 7. สร้าง payload และ compile DLL

คำสั่งเดียวนี้สร้าง glyph atlas/payload แล้ว compile plugin:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-plugin.ps1 `
  -GameRoot $GameRoot `
  -BuildPayload
```

ผลลัพธ์ local ซึ่งไม่ขึ้น Git:

```text
payload/payload.bin
payload/glyphs.png
payload/metadata.json
payload/font.ttf
build/GKThai.Plugin.dll
build/font.ttf
build/build-manifest.json
```

สคริปต์ฝัง `payload.bin`, `glyphs.png` และ `metadata.json` ใน DLL และบันทึก hash ของ input/output ทุกไฟล์

## 8. รัน tests กับ payload จริง

```powershell
python -m unittest discover -s tests
powershell -ExecutionPolicy Bypass -File tests/run-runtime-tests.ps1 -WithPayload
```

ต้องผ่านทั้ง Python tests และ C# assertions ก่อนสร้าง ZIP

## 9. สร้างแพ็ก mod

```powershell
python tools/package.py --force
```

ไฟล์สุดท้ายอยู่ที่:

```text
dist/GKThai-0.1.0-candidate.zip
```

ตรวจสมาชิก ZIP:

```powershell
tar -tf dist/GKThai-0.1.0-candidate.zip
```

ภายในต้องมี plugin สองไฟล์นี้ และเอกสาร/manifest เท่านั้น:

```text
BepInEx/plugins/GKThai/GKThai.Plugin.dll
BepInEx/plugins/GKThai/font.ttf
INSTALL_TH.md
manifest.json
```

Packager ตรวจ CRC, allowlist, embedded resource และ SHA-256 ก่อนส่งมอบ

## 10. ติดตั้งและทดสอบ local

ปิดเกมก่อน แล้วเรียก:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-plugin.ps1 -GameRoot $GameRoot
```

เปิดเกม เลือกภาษา English แล้วตรวจ:

- เมนู, บทสนทนา, inventory และ tooltip แสดงภาษาไทย
- icon และตัวเลขไม่หาย
- ข้อความหลายบรรทัดตัดคำได้
- `BepInEx/LogOutput.log` มี `GKThai ... active`
- ไม่มี error เรื่อง baseline, payload หรือ font hash

การถอนทำโดยปิดเกมแล้วนำ `BepInEx/plugins/GKThai` ออก เกมจะกลับไปใช้ locale/font เดิม เพราะม็อดนี้ไม่แก้ game assets หรือ assemblies

## 11. สิ่งที่ห้าม commit

`.gitignore` ป้องกัน `build/`, `dist/`, `payload/`, `.local/`, DLL, EXE, ZIP, TTF, Unity assets, logs และ QA captures ให้ตรวจทุกครั้งก่อน push:

```powershell
git status --short
git ls-files | Select-String -Pattern '\.(dll|exe|zip|ttf|bin|assets|png)$'
```

คำสั่งหลังต้องไม่แสดงผล ไฟล์พร้อมใช้เผยแพร่บน Nexus Mods เท่านั้น
