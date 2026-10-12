# CommitGuard Notes

what have i learned from this project will be mention in this file.
สิ่งที่ได้เรียนรู้จากโปรเจกต์นี้

## Bug 1: Ctrl-D loop
- Ctrl-D sends EOF, so readline() returns "" forever. So I fixed it by checking "" before strip().
- การ Ctrl-D แล้ว readline() ได้ "" ดังนั้นเราเลยเช็คว่า raw input มันคือ EOF ไหมถ้าใช้ ก็ abort เลยแล้วให้ผู้ใช้ commit อีกรอบ
## Bug 2: mask_snippet reveals too much
- mask snippet show the first 4 and last 4 characters of the snippet , with short words it will show to much and its gonna be predictable
- so i changed it to show the first 20% and last 20% of the snippet
- mask snippet แสดงข้อมูลมากเกินไปทำให้สามารถเดาข้อมูลได้ง่ายแก้ไขโดยแสดงเพียง 20% ของข้อมูล
