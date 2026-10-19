# Bản đồ component và hướng dẫn sửa mã nguồn

Tài liệu này chỉ rõ **muốn sửa chức năng nào thì mở file nào**. Các đường dẫn
dưới đây tính từ thư mục dự án. Mỗi component có phần chú thích đầu file:

```python
"""Chức năng: component chịu trách nhiệm việc gì.

Sửa tại đây khi: những thay đổi nên thực hiện trong file này.
Liên kết: component gọi đến hoặc sử dụng component này.
"""
# COMPONENT: nhóm.tên_component
```

Trong VS Code, nhấn **Ctrl+Shift+F** và tìm `COMPONENT:`, tên chức năng hoặc
`Sửa tại đây khi`. Có thể mở nhanh file bằng **Ctrl+P** rồi nhập tên đường dẫn.

## 1. Cấu trúc tổng thể

```text
vehiclelog/
├── __main__.py           Điểm khởi động ngắn
├── models.py             Dữ liệu dùng chung: Formula, Segment, Cursor, Project…
├── project.py            Lưu/đọc và kiểm tra project JSON
├── demo.py               Tạo dữ liệu thử có đáp án biết trước
├── ui/
│   ├── app.py            Khởi tạo QApplication
│   ├── main_window.py    Ghép các panel/controller và khởi tạo trạng thái
│   ├── theme.py          Màu, font và stylesheet
│   ├── widgets.py        Nút, nhãn, bảng, ô nhập thời gian dùng chung
│   ├── workers.py        Thực thi tác vụ ngoài luồng giao diện
│   ├── trace_preview.py  Rút gọn chuỗi công thức chỉ để hiển thị
│   ├── panels/           Bố cục từng vùng trên cửa sổ chính
│   ├── dialogs/          Form cấu hình từng chức năng
│   └── controllers/      Xử lý thao tác người dùng theo chức năng
├── readers/              Đọc BLF/MF4, quản lý DBC và điều phối import
├── calculations/         Cú pháp, đồng bộ thời gian, đơn vị, tích phân…
├── storage/              Fingerprint, ghi cache và đọc memory map
├── writers/              Xuất Excel/MF4, quản lý sheet và file tạm
├── cli/                  Các lệnh chạy không cần màn hình
├── gui.py                API tương thích → ui/
├── importers.py          API tương thích → readers/
├── formulas.py           API tương thích → calculations/
├── store.py              API tương thích → storage/
└── exports.py            API tương thích → writers/
```

Các file API tương thích giữ nguyên cách import của script cũ. Ví dụ:

```python
from vehiclelog.formulas import evaluate_all
from vehiclelog.importers import import_log
```

Muốn sửa thuật toán, hãy mở component thực thi tương ứng thay vì thêm logic
vào các file API ngắn này.

## 2. Tra nhanh phần giao diện và thao tác

| Muốn sửa | Bố cục / form | Hành vi / logic giao diện |
| --- | --- | --- |
| Màu nền, font, màu đường tín hiệu mặc định | [ui/theme.py](vehiclelog/ui/theme.py) | Hằng `STYLE`, `COLORS` |
| Kích thước cửa sổ ban đầu | [ui/main_window.py](vehiclelog/ui/main_window.py) | `MainWindow.__init__` |
| Thanh công cụ, menu, phím tắt, thanh trạng thái | [ui/panels/shell.py](vehiclelog/ui/panels/shell.py) | Callback trỏ đến controller tương ứng |
| Danh sách tín hiệu và ô tìm kiếm | [ui/panels/signals.py](vehiclelog/ui/panels/signals.py) | [ui/controllers/signals.py](vehiclelog/ui/controllers/signals.py) |
| Bố cục đồ thị, timeline và tab | [ui/panels/workspace.py](vehiclelog/ui/panels/workspace.py) | [ui/controllers/plots.py](vehiclelog/ui/controllers/plots.py) |
| Zoom, đường tín hiệu, vùng màu giai đoạn | [ui/controllers/plots.py](vehiclelog/ui/controllers/plots.py) | `_rebuild_plots`, `_range_changed`, `_overview_changed` |
| Cache đồ thị và đọc preview nền | [ui/controllers/previews.py](vehiclelog/ui/controllers/previews.py) | `_update_curves`, `_queue_previews` |
| Bảng con trỏ, màu và thời gian | [ui/panels/inspector.py](vehiclelog/ui/panels/inspector.py) | [ui/controllers/cursors.py](vehiclelog/ui/controllers/cursors.py) |
| Chọn cặp mốc, Y đầu/Y cuối, Δt/ΔY | [ui/panels/inspector.py](vehiclelog/ui/panels/inspector.py) | [ui/controllers/measurements.py](vehiclelog/ui/controllers/measurements.py), [measurements.py](vehiclelog/measurements.py) |
| Căn ngang, căn dọc, vừa màn hình | [ui/panels/workspace.py](vehiclelog/ui/panels/workspace.py) | [ui/controllers/plots.py](vehiclelog/ui/controllers/plots.py) |
| Co mọi khung đồ thị vừa viewport, không cuộn | [ui/plot_canvas.py](vehiclelog/ui/plot_canvas.py) | `FittedPlotCanvas.fit_rows`, tự gọi khi resize |
| Các cột/nút trong bảng giai đoạn, công thức, kết quả | [ui/panels/analysis.py](vehiclelog/ui/panels/analysis.py) | Controller segments/formulas tương ứng |
| Tự tạo giai đoạn M1–M2, M2–M3… | [stages.py](vehiclelog/stages.py) | [ui/controllers/segments.py](vehiclelog/ui/controllers/segments.py) |
| Form đổi tên giai đoạn (ranh giới chỉ đọc) | [ui/dialogs/segment.py](vehiclelog/ui/dialogs/segment.py) | [ui/controllers/segments.py](vehiclelog/ui/controllers/segments.py) |
| Form tạo/sửa công thức, tín hiệu, giai đoạn áp dụng | [ui/dialogs/formula.py](vehiclelog/ui/dialogs/formula.py) | [ui/controllers/formulas.py](vehiclelog/ui/controllers/formulas.py) |
| Form gán DBC theo kênh | [ui/dialogs/dbc.py](vehiclelog/ui/dialogs/dbc.py) | [ui/controllers/session.py](vehiclelog/ui/controllers/session.py) |
| Form xuất và ước tính lượng dữ liệu | [ui/dialogs/export.py](vehiclelog/ui/dialogs/export.py) | [ui/controllers/exports.py](vehiclelog/ui/controllers/exports.py) |
| Cửa sổ vẽ tín hiệu công thức | [ui/dialogs/trace.py](vehiclelog/ui/dialogs/trace.py) | `FormulasController._plot_formula_trace` |
| Mở log, giải mã lại sau đổi DBC | Form DBC ở trên | [ui/controllers/session.py](vehiclelog/ui/controllers/session.py) |
| Lưu/mở project, hỏi lưu thay đổi | Hộp thoại chọn file chuẩn Qt | [ui/controllers/project.py](vehiclelog/ui/controllers/project.py) |
| Nút demo tạo mốc, giai đoạn, công thức mẫu | Thanh công cụ | [ui/controllers/demo.py](vehiclelog/ui/controllers/demo.py) |
| Tiến độ, hủy, callback khi worker xong | Thanh trạng thái | [ui/controllers/background.py](vehiclelog/ui/controllers/background.py) và [ui/workers.py](vehiclelog/ui/workers.py) |
| Bật/tắt nút khi đang bận, kéo thả file, đóng cửa sổ | Các panel tương ứng | [ui/controllers/window.py](vehiclelog/ui/controllers/window.py) |
| Kiểu nút, bảng, nhãn dùng chung | [ui/widgets.py](vehiclelog/ui/widgets.py) | Các hàm `button`, `table`, `label`, `time_spin` |

Các panel và controller được ghép bằng **mixin** trong `MainWindow`. Nghĩa là
`self` trong `CursorsController` hay `SignalsPanel` chính là cửa sổ chính;
không tạo riêng các controller này thành cửa sổ khác. Trạng thái chia sẻ được
liệt kê trong docstring của `MainWindow`:

- `self.project`: cấu hình, tín hiệu chọn, con trỏ, giai đoạn và công thức.
- `self.store`: dữ liệu đầy đủ trên ổ đĩa.
- `self.plots`, `self.curves`: các đối tượng hiển thị.
- `self._worker`, `self._token`: tác vụ chính và yêu cầu hủy.
- `self._preview_*`: worker/cache riêng của phần đồ thị.

`ui/workers.py` có `GuiTaskRelay`, QObject nhận signal queued tại GUI thread.
Các callback progress/result/error của controller phải đi qua relay này; không
nối thẳng signal worker vào slot nằm trong Python mixin để tránh cập nhật widget
từ luồng nền. Tác vụ chính và preview có relay riêng, dọn sau khi thread kết thúc.

Luồng con trỏ mới: `cursors.py` sửa mốc → `stages.synchronize_stages` tạo đúng
n−1 giai đoạn liền kề → `measurements.py` cập nhật bảng Y/ΔY. Mốc không vượt
qua hàng xóm. Không có khóa, bám mẫu hoặc chọn cặp ranh giới thủ công trong UI.
ID giai đoạn giữ theo cặp mốc để công thức đã tick không đổi khi chỉ kéo mốc;
chia/gộp khoảng được remap lựa chọn theo phạm vi đã chọn trước đó.

## 3. Tra nhanh phần đọc và lưu dữ liệu

| Component | Trách nhiệm / vị trí sửa |
| --- | --- |
| [readers/service.py](vehiclelog/readers/service.py) | `import_log`: chọn reader, mở/tạo cache, kiểm tra nguồn/DBC không đổi |
| [readers/dbc.py](vehiclelog/readers/dbc.py) | Kiểm tra ánh xạ kênh và nạp DBC |
| [readers/blf.py](vehiclelog/readers/blf.py) | Đọc từng bản tin, đổi kênh BLF sang số hiển thị, giải mã tín hiệu, thống kê lỗi |
| [readers/mf4.py](vehiclelog/readers/mf4.py) | Đọc kênh số MF4, chuyển giá trị vật lý, giữ invalidity thành NaN |
| [readers/common.py](vehiclelog/readers/common.py) | Cờ hủy và cảnh báo số nguyên lớn bị mất độ chính xác float64 |
| [storage/identity.py](vehiclelog/storage/identity.py) | Vị trí cache mặc định và fingerprint nguồn/DBC |
| [storage/writer.py](vehiclelog/storage/writer.py) | `StoreWriter`: đăng ký tín hiệu, ghi từng khối, timestamp trùng, hoàn tất cache |
| [storage/reader.py](vehiclelog/storage/reader.py) | `SignalStore`: đọc cửa sổ, lặp mẫu đầy đủ, bao min/max đồ thị |
| [storage/schema.py](vehiclelog/storage/schema.py) | Phiên bản định dạng manifest/cache |
| [models.py](vehiclelog/models.py) | Thêm/sửa trường dữ liệu dùng chung |
| [project.py](vehiclelog/project.py) | Định dạng JSON, kiểm tra tham chiếu ID, đường dẫn tương đối |

Ngưỡng batch/chunk nằm trong reader/writer sử dụng nó. Khi thay đổi ý nghĩa
cache, xem `IMPORTER_SCHEMA` trong readers/service.py; khi thay cấu trúc cache
không tương thích, xem `SCHEMA_VERSION` trong storage/schema.py.

## 4. Tra nhanh phần công thức và năng lượng

| Component | Trách nhiệm / vị trí sửa |
| --- | --- |
| [calculations/syntax.py](vehiclelog/calculations/syntax.py) | Whitelist AST, tên hàm/số đối số, phân loại scalar/trace và tính biểu thức tại một thời điểm |
| [calculations/alignment.py](vehiclelog/calculations/alignment.py) | Hold/linear, `max_gap`, không ngoại suy |
| [calculations/context.py](vehiclelog/calculations/context.py) | Kiểm tra cấu hình, lấy tín hiệu đầu vào và chuẩn bị môi trường tính |
| [calculations/timeline.py](vehiclelog/calculations/timeline.py) | Gộp timestamp nhiều tín hiệu theo khối và chèn mốc hết hạn mẫu |
| [calculations/units.py](vehiclelog/calculations/units.py) | Các đơn vị nhận diện được, kiểm tra thứ nguyên |
| [calculations/polynomial.py](vehiclelog/calculations/polynomial.py) | Hệ số đa thức, nghiệm trong khoảng và điểm cực trị |
| [calculations/interval_splits.py](vehiclelog/calculations/interval_splits.py) | Chèn điểm đổi dấu/clip để tách xả và thu hồi đúng |
| [calculations/domains.py](vehiclelog/calculations/domains.py) | Căn bậc hai, mẫu số 0/gần 0, safe_div và cận miền giá trị |
| [calculations/integration.py](vehiclelog/calculations/integration.py) | Tích phân số, hội tụ và cực trị phi tuyến |
| [calculations/engine.py](vehiclelog/calculations/engine.py) | `evaluate_formula`, `evaluate_all`: tính kết quả từng cặp công thức–giai đoạn, độ phủ và trạng thái |
| [calculations/traces.py](vehiclelog/calculations/traces.py) | Tạo chuỗi công thức theo từng khối hoặc ghép thành mảng |
| [calculations/common.py](vehiclelog/calculations/common.py) | Ngưỡng chunk dùng chung và kiểm tra hủy |
| [ui/trace_preview.py](vehiclelog/ui/trace_preview.py) | Bao min/max chỉ để vẽ công thức, không dùng để tính tổng |

**Thay biểu thức năng lượng:** nhập trực tiếp trong form công thức. Muốn đổi
mẫu gợi ý của ứng dụng, sửa danh sách mẫu trong `ui/dialogs/formula.py`.
Muốn đổi công thức của nút Demo, sửa `ui/controllers/demo.py`; project demo đầy
đủ được tạo bởi `scripts/make_demo_project.py`.

**Thêm một hàm công thức mới:** cập nhật whitelist, số đối số và bộ tính tại
`syntax.py`, thứ nguyên tại `units.py`, phần xử lý miền tại `domains.py` nếu
cần. Hàm tổng hợp còn cần cách tích lũy trong `engine.py`. Sau đó cập nhật gợi
ý UI và thêm kiểm thử với đáp án biết trước. Không dùng `eval` cho biểu thức.

## 5. Tra nhanh phần xuất dữ liệu

| Component | Trách nhiệm / vị trí sửa |
| --- | --- |
| [writers/excel.py](vehiclelog/writers/excel.py) | Luồng xuất mẫu gốc và dữ liệu từng hàng |
| [writers/excel_sheets.py](vehiclelog/writers/excel_sheets.py) | Màu tiêu đề, độ rộng cột, tên sheet, bộ lọc và chia sheet |
| [writers/excel_metadata.py](vehiclelog/writers/excel_metadata.py) | Các cột/nội dung Summary, Signals, Segments, Formulas, Results |
| [writers/mf4.py](vehiclelog/writers/mf4.py) | Tín hiệu MF4 đã giải mã và chuỗi công thức theo giai đoạn |
| [writers/raw_mf4.py](vehiclelog/writers/raw_mf4.py) | Cấu trúc CAN_DataFrame, payload, DLC và các cờ CAN/CAN FD |
| [writers/selection.py](vehiclelog/writers/selection.py) | Tín hiệu/giai đoạn được xuất và provenance |
| [writers/atomic.py](vehiclelog/writers/atomic.py) | Bảo vệ file nguồn, file tạm, công bố kết quả và dọn khi lỗi/hủy |
| [writers/common.py](vehiclelog/writers/common.py) | Mốc bắt đầu MF4, tiến độ và hủy khi MDF.save |

Ví dụ đổi màu tiêu đề Excel: sửa `header_format` trong `_Sheets.__init__` của
`writers/excel_sheets.py`. Không cần chỉnh form xuất hoặc thuật toán năng lượng.

## 6. Điểm khởi động và CLI

- [cli/parser.py](vehiclelog/cli/parser.py): lệnh, tham số, mặc định và `--help`.
- [cli/app.py](vehiclelog/cli/app.py): dispatch, thông báo tiến độ và xử lý lỗi chung.
- [cli/options.py](vehiclelog/cli/options.py): cú pháp DBC/giai đoạn.
- [cli/inspect.py](vehiclelog/cli/inspect.py): xem metadata và signal key.
- [cli/convert.py](vehiclelog/cli/convert.py): điều phối chuyển Excel/MF4.
- [cli/analyze.py](vehiclelog/cli/analyze.py): tính project và ghi kết quả JSON.
- [cli/demo.py](vehiclelog/cli/demo.py): tạo dữ liệu demo từ dòng lệnh.
- [launch.py](launch.py): entry point dành cho PyInstaller.
- [scripts/build_windows.ps1](scripts/build_windows.ps1): tùy chọn đóng gói `.exe`.

## 7. Ví dụ lần theo một chức năng

**Nhấn “Tính kết quả”:**

```text
ui/panels/analysis.py          tạo nút và nối callback
  → ui/controllers/formulas.py  calculate: lấy công thức/giai đoạn
  → ui/controllers/background.py + ui/workers.py  chạy ngoài UI thread
  → calculations/engine.py    evaluate_all / evaluate_formula
  → calculations/context.py  đọc mẫu đầy đủ từ storage/reader.py
  → alignment/timeline/units/integration  xử lý theo timestamp
  → callback GUI             nhận FormulaResult và cập nhật bảng kết quả
```

**Thêm trường cấu hình mới vào công thức:** sửa form
`ui/dialogs/formula.py`, dataclass `Formula` trong models.py và backend sử dụng
trường đó. Project tự serialize dataclass; trường mới nên có giá trị mặc định
để mở project cũ. Nếu thêm trường trực tiếp vào `Project`, cập nhật danh sách
trường được nhận trong `project.load_project` và nơi khởi tạo/hiển thị UI.

Các module `readers`, `calculations`, `storage`, `writers` không cần Qt. Logic
xử lý dữ liệu được dùng chung giữa GUI và CLI.

## 8. Kiểm tra sau khi sửa

| Phần vừa sửa | Kiểm thử liên quan |
| --- | --- |
| Giao diện, con trỏ, giai đoạn, form | `tests/test_gui.py` |
| Đọc BLF/MF4, DBC | `tests/test_importers.py` |
| Công thức, nội suy, năng lượng | `tests/test_formulas.py` |
| Giai đoạn tự động, chia/gộp và gán công thức | `tests/test_stages.py` |
| Giá trị tại mốc, ΔY và dữ liệu thiếu/invalid | `tests/test_measurements.py` |
| Excel/MF4 đầu ra | `tests/test_exports.py` |
| Cache và project | `tests/test_store.py` |
| Cú pháp/lệnh CLI | `tests/test_cli.py` |

Chạy toàn bộ trên Linux/base environment:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Trên Windows PowerShell, sau khi cài thư viện test:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:QT_QPA_PLATFORM
```

Để tìm component bằng terminal khi có ripgrep:

```bash
rg -n 'COMPONENT:|Sửa tại đây khi:' vehiclelog
rg -n 'def calculate|def _sync_cursor|def export_excel' vehiclelog
```

Con trỏ xem nhanh: `vehiclelog/ui/controllers/hover.py` xử lý chuột và lấy mẫu gốc;
`ui/panels/workspace.py` đặt checkbox/readout; `ui/plot_canvas.py` phát sự kiện rời viewport.

Kiểm tra timestamp gốc trên đồ thị và hộp thoại xuất: `tests/test_native_time.py`.
Xuất Excel chỉ ghi mẫu gốc trong `writers/excel.py`; không còn bước lấy mẫu lại.
