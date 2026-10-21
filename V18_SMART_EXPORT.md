# V18 Smart Export (local-first)

- MP4 được xuất vào `OUTPUT/`, không yêu cầu tmpfiles.org hoặc kết nối mạng.
- Sau khi dựng, FFprobe kiểm tra dung lượng, luồng hình, thời lượng, kích thước và container.
- File được sao chép sang tên tạm, xác minh và đổi tên nguyên tử để hạn chế file MP4 dở dang.
- Nếu TTS/lồng giọng thất bại, xuất bản render gốc đã được kiểm tra, đồng thời thông báo fallback.
- Bản ghi `export.verified.json` lưu thông tin kỹ thuật ở thư mục làm việc từng video.
- V18 không thể khắc phục lỗi HTTP 403 của website ngoài; hãy dùng file tại `OUTPUT/`.

## Cài bản vá

Giải nén patch ZIP vào thư mục gốc V17 (cùng vị trí với `EDIT_TURBO_V17.bat`), cho phép ghi đè các file trong `helpers/`; sau đó chạy chế độ edit như trước.

## Cài mới

Giải nén gói FULL, chạy `SETUP_ONCE.bat` rồi `EDIT_TURBO_V18.bat`.
