# หลักฐาน QA — GKThai ภาคแรก 0.1.0

ตรวจวันที่ 22 กันยายน 2026 ทั้งบนสำเนาเกมฐาน pristine และ installation ที่ใช้งานจริง:

- Graveyard Keeper 1.407 / Unity 2020.3.17f1 / Windows x64 Mono
- BepInEx 5.4.23.5 และ Harmony 2.9.0.0
- `resources.assets` SHA-256 `215c7981901a4b72d5db717666ba47ad3cc032527c95f58dc39d8af1293a69ca`
- `Assembly-CSharp-firstpass.dll` SHA-256 `9dc6def3b7715dd27eeb168ddc0af47e31c6f38d3fbee24bf592899392026498`
- `Assembly-CSharp.dll` SHA-256 `e72e4270e4b88dd0a87ca23c9cf1750aec4c4a0fedb40b6d2dae7902fc9c7fd8`

## ผลอัตโนมัติ

- Python payload/package tests: 19 tests ผ่าน
- C# payload/metrics tests: 12 assertions ผ่านกับ payload จริง
- Runtime QA: `RESULT failures=0`
- โหลด plugin สำเร็จ ฟอนต์ 7 แบบ, atlas clone 1 ชุด และคำแปล Unicode 10,961 แถว
- ตรวจทุกฟอนต์ว่า bind ได้, raw `UILabel.text` ยังคง Unicode ไทย, `processedText` จึงค่อยเป็น PUA, callback ไม่เห็น PUA, glyph lookup ซ้ำไม่สะสม scale และ width ตรงกับ advance
- UIInput ถูกยกเว้นจากการแปลง PUA
- CJK เดิมยังใช้กฎเดิม และ PUA ของไทยใช้ ZWSP สำหรับตัดคำ
- สลับ `en → de → en` แล้วฟอนต์เดิมถูกคืนและฟอนต์ไทยถูก bind กลับ
- `Resources.Load<GJL>("Locales/lng_en")` และ dictionary อังกฤษต้นฉบับในหน่วยความจำไม่ถูกแก้
- หลังย้าย plugin ออก เกมกลับเป็น English/font เดิม และ runtime QA baseline มี `RESULT failures=0`
- SHA-256 ของ game assets/DLL ทั้งสามไฟล์ก่อนและหลังเปิดเกมพร้อม plugin และหลังถอนตรงกับ pristine ทุกไฟล์
- ติดตั้งจริงที่ `BepInEx/plugins/GKThai` แล้ว โดยมีเฉพาะ `GKThai.Plugin.dll` และ `font.ttf`
- Runtime QA บน installation จริงผ่าน `RESULT failures=0` พร้อม Configuration Manager ที่ติดตั้งอยู่เดิม
- หลัง runtime QA ไฟล์เกมหลักทั้งสามรายการยังมี SHA-256 ตรงกับ pristine

เก็บหลักฐานข้อความจาก sandbox ไว้ใน `docs/evidence/runtime-qa.txt` และ `uninstall-baseline-qa.txt` หลักฐานจาก installation จริงอยู่ใน `docs/evidence/actual-game-runtime-qa.txt` ภาพ QA ถูกเก็บไว้นอก Git repository

## ขอบเขตที่ยังต้องตรวจโดยคน

ยังไม่ได้เล่นครบทุกฉากและทุก DLC ต้องตรวจเพิ่ม: บทสนทนายาว, tooltip เทคโนโลยี, inventory, icon/ตัวเลข, controller prompts, ข้อความหลายบรรทัด และความคมชัดในความละเอียดหน้าจอที่ใช้จริง การผ่าน corpus/tests ไม่รับรองคุณภาพความหมายของคำแปลทุกบรรทัด

ชุดนี้ไม่เคยเขียน `Graveyard Keeper_Data`, ไม่ใช้ binary patcher ระหว่าง runtime และไม่รวม QA probe ใน release ZIP
