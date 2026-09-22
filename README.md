# Graveyard Keeper BepInEx Thai Plugin

ม็อดภาษาไทยสำหรับ **Graveyard Keeper ภาคแรก** รุ่น Windows Steam `1.407` ทำงานผ่าน BepInEx และ Harmony ในหน่วยความจำ โดยไม่แก้ `resources.assets` หรือ DLL ของเกมบนดิสก์

## ดาวน์โหลดม็อดพร้อมใช้

Repository นี้เก็บ source code, คำแปล และเครื่องมือ build เท่านั้น **ไม่มีไฟล์ม็อดที่ compile แล้ว ไม่มี `font.ttf` และไม่มีไฟล์เกม** ผู้เล่นทั่วไปให้ดาวน์โหลดแพ็กพร้อมใช้จาก [Graveyard Keeper Mods บน Nexus Mods](https://www.nexusmods.com/graveyardkeeper/mods/184) โดยค้นหา `GK2Thai` แล้วทำตาม [คู่มือติดตั้ง](docs/INSTALL_TH.md)

แพ็กพร้อมใช้ต้องมีไฟล์ต่อไปนี้:

```text
BepInEx/plugins/GK2Thai/
├── GK2Thai.Plugin.dll
└── font.ttf
```

## คุณสมบัติ

- แทนภาษา English (`en`) ด้วยคำแปลไทย 10,961 รายการ
- รองรับฟอนต์ NGUI 7 แบบ, Thai shaping, HD2 glyph และการตัดคำภาษาไทย
- รักษา icon token, placeholder, ตัวเลข และ markup ของเกม
- ตรวจ SHA-256 ของเกม, payload และฟอนต์ก่อนเปิดใช้งาน
- ถอนม็อดได้ด้วยการนำโฟลเดอร์ `BepInEx/plugins/GK2Thai` ออก

## Build จาก source

อ่าน [คู่มือ Build ตั้งแต่เริ่มจนได้ ZIP](docs/BUILD_TH.md) คู่มือนี้ครอบคลุมการเตรียมเกม, BepInEx, Python, ฟอนต์, การตรวจคำแปล, build payload, compile DLL, tests, packaging และติดตั้งทดสอบ

## โครงสร้างสำคัญ

```text
GK2Thai.Plugin/       C# runtime plugin และ Harmony patches
translations/th.csv  คำแปล Unicode ไทย
config/               ค่า font pipeline และรายการ token ของเกม
tools/                payload builder, source exporter และ packager
tests/                Python/C# tests และ runtime QA probe
docs/                 คู่มือติดตั้ง, build และ QA
```

ไฟล์ที่สร้างระหว่าง build อยู่ใน `payload/`, `build/` และ `dist/` ซึ่งถูก `.gitignore` ไว้ทั้งหมด

## สถานะรองรับ

- Graveyard Keeper `1.407`
- Unity `2020.3.17f1`, Windows x64 Mono
- BepInEx `5.4.23.5`

หากเกมอัปเดตจน SHA-256 เปลี่ยน BuildGuard จะหยุดม็อดเพื่อป้องกันการ patch ผิดรุ่น ต้องตรวจจุด hook และออก build ใหม่ก่อนเพิ่ม baseline
