# GKThai สำหรับ Graveyard Keeper ภาคแรก

รุ่น `0.1.0` ผ่าน runtime QA บนเกมติดตั้งจริงแล้ว แต่ยังต้องเล่นตรวจหลายฉากด้วยคน ใช้กับภาคแรกเท่านั้น ไม่ใช้กับ GK2 Demo หรือตัวเต็ม ดูหลักฐานใน `docs/QA_TH.md` ของ source repository

## ก่อนติดตั้ง

ต้องมี BepInEx 5 รุ่น Windows x64 ที่รองรับ Unity Mono และใช้เกมฐานต้นฉบับที่ตรงกับ BuildGuard ก่อนเปิด plugin

หากเคยใช้แพ็กภาษาแบบแก้ `resources.assets` หรือ game DLL ให้สำรองของเดิม แล้วใช้ Steam Verify คืนไฟล์ต้นฉบับก่อนติดตั้ง การวาง plugin นี้ทับเกมที่ถูก patch จะถูก BuildGuard ปฏิเสธ ไม่มีการคืนไฟล์เกมอัตโนมัติใน plugin หรือ installer

ฐานที่รองรับ:

| ไฟล์ | SHA-256 |
|---|---|
| `Graveyard Keeper_Data/resources.assets` | `215c7981901a4b72d5db717666ba47ad3cc032527c95f58dc39d8af1293a69ca` |
| `Graveyard Keeper_Data/Managed/Assembly-CSharp-firstpass.dll` | `9dc6def3b7715dd27eeb168ddc0af47e31c6f38d3fbee24bf592899392026498` |
| `Graveyard Keeper_Data/Managed/Assembly-CSharp.dll` | `e72e4270e4b88dd0a87ca23c9cf1750aec4c4a0fedb40b6d2dae7902fc9c7fd8` |

ตรวจใน PowerShell ด้วย `Get-FileHash -Algorithm SHA256 -LiteralPath '<path>'` หาก hash ต่างต้องตรวจรุ่นและ rebuild ห้ามปิด BuildGuard เพื่อบังคับโหลด

## ติดตั้งจาก ZIP

1. ปิดเกม
2. แตก ZIP แล้วคัดลอกโฟลเดอร์ `BepInEx` ไปไว้ในรากเกมที่ตรวจฐานแล้ว
3. ตรวจว่าภายใต้ `BepInEx/plugins/GKThai/` มีเพียง `GKThai.Plugin.dll` และ `font.ttf`
4. เปิดเกมและเลือกภาษา **English (`en`)** ซึ่งเป็นช่องที่แพ็กไทยแทนข้อความ
5. ตรวจ `BepInEx/LogOutput.log` ว่า plugin เปิดใช้งานโดยไม่มีข้อผิดพลาดด้าน baseline, payload หรือ font แล้วตรวจภาษาไทย ตัวเลข ไอคอน และการขึ้นบรรทัดในเมนู/บทสนทนา

คำแปล, cluster map และ glyph ที่สร้างจากฟอนต์ถูกฝังใน DLL แล้ว ผู้เล่นไม่ต้องติดตั้ง Python แพ็กนี้ไม่แจก game DLL/assets ที่แพตช์แล้ว และไม่เขียน `Languages/en` หรือ `Graveyard Keeper_Data` การเปลี่ยนข้อความและฟอนต์เกิดในหน่วยความจำผ่าน BepInEx/Harmony

## ฟอนต์และการ rebuild

ค่าปัจจุบันคือ scale **0.7**, raster density **2 (HD2)**, ช่องไฟ **0.1**, digit spacing **1** ใช้ `font.ttf` ที่ตรงกับ SHA-256 ใน metadata เท่านั้น:

`98560a50f5c6430f8e6570fd315a0bf056470eb72e7fb812148f17fcfec4dd57`

รูป glyph สร้างล่วงหน้าจากฟอนต์นี้แล้วฝังใน DLL การเปลี่ยน `font.ttf` อย่างเดียวไม่เปลี่ยนภาพที่วาด และ plugin จะปฏิเสธเมื่อ hash ไม่ตรง หากต้องการเปลี่ยนฟอนต์ ให้ปรับ config/font ฝั่ง source แล้วสร้าง payload และ DLL ใหม่ด้วยกัน

สำหรับผู้พัฒนา ดูขั้นตอนครบใน `docs/BUILD_TH.md` หรือเรียกจาก repository ที่ clone ไว้ใต้ `mods/GKThai`:

```powershell
python mods/GKThai/tools/build_payload.py --game-root "$PWD"
powershell -ExecutionPolicy Bypass -File mods/GKThai/build-plugin.ps1 -GameRoot "$PWD"
python -m unittest discover -s mods/GKThai/tests
python mods/GKThai/tools/package.py
```

ตัว package ตรวจว่า source ที่ระบุใน build manifest ยังตรงกับตอน build, embedded resources ตรงกับ payload, ฟอนต์ถูกต้อง และ ZIP ผ่าน CRC/member/hash checks หากไฟล์ปลายทางมีอยู่แล้วต้องระบุ `--force` จึงจะแทนที่ได้

## ถอนม็อด

ปิดเกมแล้วนำโฟลเดอร์ `BepInEx/plugins/GKThai` ออก บนฐาน pristine เกมจะกลับมาใช้ข้อความและฟอนต์เดิมโดยไม่ต้องคืน game DLL/assets จากแพ็กนี้ ไฟล์ config/log ของ BepInEx อาจยังคงอยู่และไม่ใช่ส่วนของสองไฟล์ plugin

หากยังพบภาษาไทยหลังถอน ให้ตรวจว่าฐานเกมยังมีแพ็กเก่าแบบแก้ไฟล์ติดตั้งอยู่หรือมี plugin ภาษาอื่นหรือไม่ การถอน plugin นี้ไม่คืนไฟล์ที่ถูกแพตช์จากระบบเดิม
