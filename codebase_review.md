# Đánh Giá Mã Nguồn & Các Giải Pháp Đã Triển Khai

Tài liệu này ghi lại quá trình đánh giá mã nguồn dự án `ai-coding-config`, các vấn đề kỹ thuật nghiêm trọng phát hiện được và cách thức khắc phục cụ thể.

---

## 🔍 1. Các Vấn Đề Đã Được Khắc Phục

### 🛡️ Lỗi Tranh Chấp Profile Playwright (Browser Lock)
*   **Vấn đề:** Khi chạy song song nhiều CLI (Claude Code, Codex, agy) cùng sử dụng Playwright MCP, xảy ra lỗi xung đột khóa trình duyệt (`Browser is already in use`). Nguyên nhân do các công cụ dùng chung một thư mục profile chromium mặc định.
*   **Giải pháp:** Bổ sung tham số `--isolated` vào cấu hình Playwright MCP trong tất cả các tệp cấu hình của ba CLI (`~/.claude.json`, `~/.codex/config.toml`, `~/.gemini/config/mcp_config.json`). Khi có cờ này, mỗi phiên làm việc Playwright sẽ khởi tạo profile chromium độc lập trong một thư mục tạm thời riêng biệt.

### 🔑 Quyền Administrator/Developer Mode trên Windows khi tạo Symlink
*   **Vấn đề:** Trên Windows, script cài đặt trước đó sử dụng `mklink /d` để tạo liên kết thư mục (directory symbolic link). Chức năng này yêu cầu quyền Administrator hoặc phải kích hoạt Windows Developer Mode. Nếu không, quá trình cài đặt sẽ báo lỗi và phải chuyển sang sao chép thư mục (khiến cấu hình không tự động đồng bộ khi sửa đổi trong repo).
*   **Giải pháp:** Tối ưu hóa trong `install.sh`, chuyển đổi từ `mklink /d` sang `mklink /j` (**Directory Junctions**). Directory Junctions không yêu cầu bất kỳ quyền đặc quyền nào trên Windows, giúp người dùng phổ thông chạy cài đặt mượt mà.

### ⏳ Treo Script Cài Đặt khi Chạy trên Git Bash (Windows)
*   **Vấn đề:** Git Bash tự động biên dịch các đường dẫn dạng `/c` thành `C:\` khi gọi các ứng dụng Windows gốc như `cmd.exe`. Lỗi dịch đường dẫn làm cho lệnh tạo symlink bị treo và mở ra một shell tương tác phụ.
*   **Giải pháp:** Bổ sung tiền tố `MSYS_NO_PATHCONV=1` trước khi gọi `cmd.exe /c mklink`. Điều này tắt tính năng tự động chuyển đổi đường dẫn của MSYS, giúp lệnh thực thi ngay lập tức và chính xác.

### 🧩 Lỗi Thiếu Tạo Liên Kết Custom Agents cho `agy`
*   **Vấn đề:** Ở khối cấu hình Antigravity CLI (`agy`), script chỉ tạo thư mục rỗng `~/.gemini/config/agents` mà không liên kết các file agents dạng markdown từ thư mục `claude/agents/*.md` của repo vào đây.
*   **Giải pháp:** Bổ sung vòng lặp tìm kiếm và liên kết các file agents tương tự như cấu hình của Claude Code. Giúp `agy` nhận diện đầy đủ các custom agents ngay sau khi cài đặt.

### 📁 Theo Dõi Thư Mục `hooks` & Tối Ưu Hóa Cảnh Báo
*   **Vấn đề:** Thư mục `claude/hooks` trống không được Git theo dõi, dẫn đến việc thiếu thư mục này trên máy của người dùng khác và sinh ra cảnh báo phiền phức `[WARN] No hooks to install`. Đồng thời, việc sử dụng vòng lặp `claude/hooks/*` mà không kiểm tra tệp tin thực sự dẫn đến lỗi đường dẫn đại diện `*` khi thư mục chỉ chứa file ẩn `.gitkeep`.
*   **Giải pháp:**
    1.  Tạo tệp `.gitkeep` trong `claude/hooks/` để đảm bảo Git luôn theo dõi thư mục này.
    2.  Sửa đổi script `install.sh`: Chỉ liên kết các tệp tin hợp lệ (`[ -f "$f" ]`), tự động bỏ qua các thư mục hoặc tệp tin đại diện không tồn tại và ẩn cảnh báo warning không cần thiết nếu người dùng không định nghĩa hook nào.

---

## 📝 2. Đánh Giá Đề Xuất về Các Liên Kết ECC Rules Bị Hỏng (`../common/`)

*   **Vấn đề:** Các file cấu hình ECC rules trong thư mục `claude/rules/ecc/` chứa các dòng tham chiếu kế thừa như `> This file extends [common/coding-style.md](../common/coding-style.md) ...`. Tuy nhiên thư mục `common/` đã bị xóa hoàn toàn từ commit `1b63649` vì mục đích loại bỏ các quy tắc không sử dụng. Điều này khiến các liên kết này bị hỏng (broken links).

### 💡 Khuyến Nghị & Quyết Định Thiết Kế:
1.  **Tại sao không tải lại từ `affaan-m/ECC`?**
    - Repository gốc chứa nhiều quy tắc chung chung (như model selection, context limits) đã được tích hợp sẵn hoặc không hoàn toàn phù hợp với cấu hình riêng của dự án này.
    - Việc tải thêm thư mục `common/` sẽ làm tăng độ phức tạp của dự án và làm loãng các thiết lập đã được tinh chỉnh riêng.
2.  **Giải pháp xử lý:**
    - Thay vì tải lại mã nguồn từ bên ngoài, chúng ta nên giữ nguyên trạng thái tối giản hiện tại.
    - Các liên kết dạng `[common/coding-style.md](../common/coding-style.md)` trong tiêu đề chỉ đóng vai trò ghi chú nguồn gốc (metadata) để lập trình viên biết quy tắc này kế thừa ý tưởng từ đâu, không ảnh hưởng đến hoạt động phân tích của AI (vì AI đọc trực tiếp file quy tắc cụ thể trong `rules/ecc/` và không cố truy cập liên kết tương đối đó qua trình duyệt).
    - Do đó, chúng ta **không cần khôi phục** thư mục `common/`.
