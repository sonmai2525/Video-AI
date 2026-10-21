# VIDEO AI EDITOR V17 — Turbo cache + compact planning

- Cache kết quả phân tích theo đường dẫn, kích thước, nanosecond mtime, mẫu nội dung đầu/cuối file, chế độ quét và ngưỡng cắt. Cache lưu ở thư mục người dùng `~/.video_ai_editor_cache_v17` để tái sử dụng giữa các lần xuất video.
- `--no-cache` để phân tích lại; `--cache-dir <folder>` chỉ định cache tùy chọn (trên `helpers/auto_viral_editor.py`).
- Turbo gộp EDL/V5/V6/V12/V15 vào **một** tiến trình Python thay vì nhiều lần khởi động; giữ logic lựa chọn cảnh và thứ tự hiệu ứng giống bản trước.
- Smart/Max vẫn giữ quy trình cũ (ngoại trừ sử dụng analysis cache) để bảo toàn khả năng dựng chuyên sâu.
- `EDIT_TURBO_V17.bat`: chạy chế độ Turbo mới. File BAT V16 vẫn tương thích.
- `helpers/benchmark_v17.py`: đo phân tích lần đầu/lần hai, báo kết quả thay vì công bố phần trăm tăng tốc không có kiểm chứng.

Lưu ý: phân tích ngữ nghĩa nội dung *chưa* được thêm vì chương trình hiện chưa tích hợp mô hình thị giác-ngôn ngữ thực sự. Cache dùng metadata và fingerprint một phần, không phải hash toàn bộ file; với nguồn được sửa nhưng giữ nguyên cả timestamp và phần đầu/cuối, sử dụng `--no-cache`.
