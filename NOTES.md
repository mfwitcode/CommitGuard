# CommitGuard Notes

what have i learned from this project will be mention in this file.
สิ่งที่ได้เรียนรู้จากโปรเจกต์นี้

## Issue 1: Ctrl-D loop
- Ctrl-D sends EOF, so readline() returns "" forever. So I fixed it by checking "" before strip().
- การ Ctrl-D แล้ว readline() ได้ "" ดังนั้นเราเลยเช็คว่า raw input มันคือ EOF ไหมถ้าใช้ ก็ abort เลยแล้วให้ผู้ใช้ commit อีกรอบ
## Issue 2: mask_snippet reveals too much
- mask snippet show the first 4 and last 4 characters of the snippet , with short words it will show to much and its gonna be predictable
- so i changed it to show the first 20% and last 20% of the snippet
- mask snippet แสดงข้อมูลมากเกินไปทำให้สามารถเดาข้อมูลได้ง่ายแก้ไขโดยแสดงเพียง 20% ของข้อมูล
## Issue 3: hook not detected commitguard.py in hook
- hook found no commitguard.py in a folder that being commit
- so we find where do commitguard.py really lives and write the full address into the script
- hook หา commitguard.py ในโฟลเดอร์ที่กำลังถูก commit ไม่เจอแก้โดยการหา absolute path ของ commitguard.py ตั้งแต่ตอนติดตั้งและเขียนลงไปในไฟล์ hook
## Issue 4: install replaces pre-commit hook and uninstall deletes hook without user notice
-install replaced any existing pre-commit hook and uninstall deleted it, so a user hook could be lost without notice. 
-Now the hook has a marker comment and both commands refuse to touch a hook without it
-การ install แทนที่ไฟล์ pre-commit ที่มีอยู่แล้วและ uninstall ลบ hook ที่มีอยู้แล้วแม้ว่ามันไม่ใช่ไฟล์ที่ commit guard สร้างขึ้น
-แก้ใส่การ marker ลงไปใน hook uninstall จะได้เช็คว่าสร้างโดย CommitGuard ไหม