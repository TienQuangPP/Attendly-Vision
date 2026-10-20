# Attendly Vision

**Điểm danh thông minh bằng khuôn mặt — ứng dụng desktop cho Windows.**

Nhận diện ArcFace, phát hiện khuôn mặt SCRFD, giao diện tiếng Việt và lưu dữ liệu tại máy.

## Tải và chạy

Tải `AttendlyVision-Windows-x64.zip` tại [Releases](https://github.com/TienQuangPP/Attendly-Vision/releases/latest), giải nén toàn bộ rồi mở
`AttendlyVision.exe`. Giữ thư mục `_internal` cạnh file EXE; không cần cài Python.
Lần đầu vào phiên điểm danh cần Internet để InsightFace tải mô hình `buffalo_sc`.
Các lần tiếp theo có thể dùng webcam và nhận diện ngoại tuyến.

1. Tạo lớp / môn học.
2. Chọn slot, thời lượng và webcam hoặc IP camera RTSP.
3. Đăng ký sinh viên bằng mã sinh viên, họ tên và ảnh khuôn mặt.
4. Bật nhận diện tự động và xem kết quả điểm danh.
5. Xuất bảng Excel hoặc tra lịch sử điểm danh.

## Tính năng

- Webcam và RTSP, tự kết nối lại khi luồng camera gián đoạn.
- Phát hiện khuôn mặt, landmark, đăng ký và so khớp embedding.
- Chặn nhận diện khi có nhiều khuôn mặt đáng kể trong khung hình.
- Quản lý lớp, môn, slot học và sinh viên.
- Lưu điểm danh SQLite, xuất Excel, chụp khuôn mặt.
- Có tiền xử lý ánh sáng; chống giả mạo mặc định tắt và chưa được kiểm định.

## Dữ liệu

Mặc định lưu trong `%LOCALAPPDATA%\AttendlyVision`: cơ sở dữ liệu, ảnh đăng ký,
embedding, các phiên học, ảnh chụp, mô hình và log. Thay vị trí bằng biến môi trường
`ATTENDLY_DATA_DIR`. Sao lưu thư mục này trước khi thay máy.

Kho mã nguồn và bản phát hành không chứa dữ liệu sinh viên, ảnh cá nhân, lịch sử
điểm danh, báo cáo PDF/Word/PowerPoint hoặc trọng số mô hình.

## Chạy từ mã nguồn

Yêu cầu Python 3.11 x64. Chạy `setup.bat`, sau đó `run.bat`.

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r attendance_system/requirements.txt
.venv\Scripts\python.exe attendance_system/main.py
```

## Đóng gói Windows

Sau khi cài thư viện, chạy `powershell -ExecutionPolicy Bypass -File build.ps1`.
Kết quả nằm trong `dist/AttendlyVision-Windows-x64.zip`.

Kiểm tra bản đóng gói: `AttendlyVision.exe --self-test` (giao diện và SQLite),
hoặc thêm `--check-models` để kiểm tra tải mô hình và suy luận trên khung hình trống.
Kết quả lưu tại `self-test.json` trong thư mục dữ liệu.

## Cấu hình và giới hạn

Ngưỡng so khớp mặc định `0.60`, chênh lệch giữa hai danh tính `0.08` trong
`attendance_system/config.py`. Cần hiệu chỉnh theo camera, ánh sáng và dữ liệu thực.
Chỉ đăng ký dữ liệu khuôn mặt khi có sự đồng ý phù hợp; kiểm tra thủ công kết quả
trước khi dùng cho điểm danh chính thức. Đây là dự án học tập/nghiên cứu.

Xem `THIRD_PARTY_NOTICES.md` để biết thư viện và điều kiện sử dụng mô hình.
