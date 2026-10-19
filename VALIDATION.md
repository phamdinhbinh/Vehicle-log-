# Kết quả kiểm chứng bản 0.1.0

## Cập nhật căn đồ thị và giai đoạn liền kề

Kiểm thử toàn bộ: **109 passed in 5.87s**; 8 cảnh báo deprecation đến từ
pyqtgraph với NumPy 2.5 trong kiểm tra geometry, không có kiểm thử thất bại.

- Kiểm tra 15 tín hiệu đều nằm trong viewport ở 1500×980, 1100×750, 1700×1000,
  không có thanh cuộn đồ thị; các nút căn X/Y đưa đúng trục về dữ liệu.
- Con trỏ sắp theo thời gian; đúng n−1 giai đoạn M1–M2, M2–M3…; kiểm tra
  thêm, xóa, kéo, giới hạn không đi xuyên mốc và chuyển project cũ.
- Kiểm tra giữ gán công thức khi kéo mốc, kế thừa khi chia/gộp có kiểm soát,
  và tích phân năng lượng chỉ theo ranh giới/giai đoạn đã chọn.
- Đối chiếu Y đầu/Y cuối, ΔY có dấu, Δt; ngoài dữ liệu hoặc invalid trả trống.
- Sửa lỗi callback Qt trong Python mixin: dùng GuiTaskRelay (QObject) nhận queued
  signal để progress/result/error luôn về GUI thread. Có regression test chạy
  ba tác vụ liên tiếp, đối chiếu thread của mọi lần cập nhật widget.
- Chạy thật nút Demo → import → ba lần tính liên tiếp: 4 con trỏ, 3 giai đoạn,
  mỗi lần 3 năng lượng + 3 trace, không lỗi. Ảnh desktop-preview.png đã cập nhật.

Các kết quả dưới đây là lịch sử kiểm chứng của bản nền và lần tách component.

## Kiểm chứng sau khi tách component

Đã tách giao diện, đọc/ghi log, tính toán, cache và CLI thành các module theo
chức năng, giữ API công khai hiện có. Thay đổi phục vụ tìm kiếm/chỉnh sửa mã;
không thêm chức năng xử lý dữ liệu trong lần tái cấu trúc này.

`QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`:
**94 passed in 5.39s**. `compileall` toàn bộ package/scripts thành công.

Các kiểm thử dùng chi tiết nội bộ (ngưỡng chunk/grid) đã chuyển điểm patch
sang đúng component sở hữu; các assertion về dữ liệu và kết quả giữ nguyên.
Riêng phần công thức đã đối chiếu AST của 28 hàm/class sau chuẩn hóa tên và
docstring, xác nhận giữ nguyên thuật toán.

Bản đồ chỉnh sửa tại [CODE_MAP.md](CODE_MAP.md); mọi module trong vehiclelog
có marker `COMPONENT:` và mô tả chức năng/vị trí sửa bằng tiếng Việt.

Môi trường: Linux, Python 3.12.14. Giao diện được chạy Qt offscreen; chưa kiểm
tra tương tác trên màn hình Windows hoặc tạo bản Windows executable.

## Kiểm thử

`QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`

**94 passed in 5.82s**. Bao gồm:

- BLF/DBC thực: kênh, Motorola, signed, multiplexing, scale, enum số, lỗi payload.
- Cache: timestamp trùng, bảo vệ timestamp đi lùi, source/DBC thay đổi, hủy tác vụ.
- MF4: giá trị vật lý, mẫu invalid, cảnh báo mất độ chính xác số nguyên lớn.
- Công thức: AST, hold/linear, tín hiệu lệch nhịp, ranh giới, tích phân, đổi dấu,
  khoảng mất mẫu, cực trị, `safe_div`, gán giai đoạn, xử lý theo khối.
- Excel: native/raster, khoảng trống, chia hàng/cột, provenance, kết quả công thức.
- MF4 xuất: native, invalidity, giai đoạn, chuỗi công thức, dữ liệu CAN FD thô,
  giải mã lại bằng DBC, hủy khi ghi, bảo vệ nguồn/đích.
- CLI và GUI: pipeline, worker ngoài UI thread, cập nhật UI qua callback,
  con trỏ/giai đoạn, công thức, cache đồ thị, preview công thức giới hạn bộ nhớ.

`python -m compileall -q vehiclelog scripts`: thành công.

`python -m pip check`: No broken requirements found.

Cài package editable và entry point `vehicle-log-studio --help`: thành công.

## Đối chiếu demo toàn hành trình 120 giây

Điện áp 400 V; dòng 50 A trong 40 s, -20 A trong 40 s, 30 A trong 40 s;
tốc độ 36 km/h. Giữ giá trị trước theo timestamp (hold).

| Chỉ tiêu | Kết quả |
| --- | ---: |
| Năng lượng ròng | 0.2666666667 kWh |
| Năng lượng xả | 0.3555555556 kWh |
| Năng lượng thu hồi | 0.0888888889 kWh |
| Quãng đường | 1.2 km |
| Mức tiêu thụ | 22.2222222222 kWh/100 km |

`scripts/verify_demo.py` đã tạo và đọc lại:

- `examples/verified-output/stage-report.xlsx`: đủ 9 sheet, kết quả và raster.
- `examples/verified-output/stages-decoded.mf4`: 16 nhóm gồm 3 tín hiệu và
  công suất tính toán cho 4 giai đoạn, giữ nhãn và provenance.
- `examples/verified-output/can-raw.mf4`: giải mã lại với DBC bằng asammdf,
  đủ 1.201 mẫu điện áp, tất cả 400 V.
- `examples/verified-output/verification.json`: toàn bộ kết quả theo giai đoạn.

GUI demo chạy import → calculate ở background, cho 3 kết quả năng lượng và
3 công thức công suất dạng trace. Ảnh tại `examples/desktop-preview.png` và
`examples/formula-preview.png` được chụp từ ứng dụng thật với dữ liệu tổng hợp.

## Phép thử tổng hợp bộ nhớ

`python scripts/benchmark_store.py --samples 1000001 --chunk 100000`

| Đại lượng | Số đo |
| --- | ---: |
| Tổng giá trị | 2.000.002, gồm 2 tín hiệu |
| Khối ghi | 100.000 mẫu |
| Dung lượng cache | 32.000.755 byte |
| Thời gian ghi | 0.0451 s |
| Thời gian tính năng lượng | 1.0022 s |
| Peak RSS ban đầu | 30.71 MiB |
| Peak RSS sau ghi | 36.67 MiB |
| Peak RSS sau tính | 63.30 MiB |
| Năng lượng | 22.2222222222 kWh, khớp tham chiếu |

Số đo có thể thay đổi theo máy và tải đang chạy; RSS gồm cả các trang memory
map được hệ điều hành giữ trong RAM. Đây là kiểm tra store/công thức với dữ
liệu tổng hợp, **chưa phải phép đo hiệu năng đọc BLF 3 GB**.

## Phần cần nghiệm thu trên máy đích

- BLF/DBC thực, số kênh/tín hiệu và chu kỳ lấy mẫu của xe.
- Quy ước dấu, đơn vị và vị trí đo dùng để tính năng lượng.
- Thời gian xử lý, RAM và dung lượng cache với file khoảng 3 GB.
- Mở MF4 bằng đúng phiên bản phần mềm người dùng đang dùng.
- Giao diện tương tác và gói Windows tạo từ `scripts/build_windows.ps1`.
