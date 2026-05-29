// MachineStatus.h - Danh sách mã trạng thái máy rang
// Ghi vào thanh ghi STT_W trên HMI khi trạng thái thay đổi
// Hàm detectMachineStatus() và updateMachineStatus() nằm trong Program.h
//
// Phạm vi mã (bắt đầu từ 1):
//   1        = Nghỉ
//   2-20     = Hệ thống / Khởi động
//   21-50    = Làm nóng máy rang
//   51-80    = Bước rang (progStep)
//   81-100   = Sự kiện rang
//   101-120  = Thẻ nhớ SD / hồ sơ rang
//   121-140  = Điều áp hút / chỉnh tốc độ gió tự động
//   141-160  = Sự kiện màn hình HMI / điều khiển từ máy tính
//   161-180  = Đầu đốt / gió / trống rang
//   201-220  = Cơ cấu chấp hành
//   221-240  = Cấp liệu / tách đá / nạp liệu tự động
//   241-260  = Cân / trọng lượng
//   261-280  = Cảnh báo cảm biến / nhiệt độ
//   281-300  = Lỗi truyền thông Modbus
//   301-320  = Kết quả kiểm tra khi khởi động
//   321-350  = Bộ điều khiển tốc độ tăng nhiệt
//   351-380  = Học nhiệt / bảng học tự động
//   401-430  = Lỗi nghiêm trọng

#pragma once
#include "Define.h"

// [1] Nghỉ
#define STT_IDLE                    1   // Máy rang đang nghỉ, không hoạt động

// [2-20] Hệ thống / Khởi động
#define STT_SYSTEM_BOOT             2   // Hệ thống đang khởi động
#define STT_SYSTEM_READY            3   // Tất cả thiết bị OK, máy sẵn sàng hoạt động
#define STT_SYSTEM_RESET            4   // Hệ thống vừa được khởi động lại
#define STT_DEBUG_ON                5   // Chế độ gỡ lỗi đang bật
#define STT_MODBUS_ID_CHANGED       6   // Đã đổi ID Modbus, cần khởi động lại máy
#define STT_MODBUS_BAUD_CHANGED     7   // Đã đổi tốc độ Modbus, cần khởi động lại
#define STT_PC_CONTROL_ON           8   // Điều khiển từ máy tính (Artisan) đang bật
#define STT_PC_CONTROL_OFF          9   // Tắt điều khiển máy tính, chuyển về màn hình HMI
#define STT_SD_INIT_OK              10  // Thẻ nhớ SD khởi tạo thành công
#define STT_SD_INIT_FAIL            11  // Không tìm thấy hoặc lỗi thẻ nhớ SD
#define STT_DATE_TIME_SYNC          12  // Đang đồng bộ đồng hồ thời gian thực
#define STT_PROFILE_SCAN            13  // Đang quét ngày giờ các hồ sơ rang trên SD

// [21-50] Làm nóng máy rang
#define STT_PREHEAT_START           21  // Người dùng bấm nút làm nóng máy, bắt đầu
#define STT_PREHEAT_COOLING         22  // Nhiệt độ BT cao hơn mức đích, chờ máy nguội bớt
#define STT_PREHEAT_IGNITING        23  // Đang bật đầu đốt
#define STT_PREHEAT_IGNITE_RETRY    24  // Bật đầu đốt thất bại, đang thử lại
#define STT_PREHEAT_IGNITE_FAIL     25  // Bật đầu đốt thất bại sau 3 lần thử
#define STT_PREHEAT_IGNITE_OK       26  // Đầu đốt đã bật thành công, có tín hiệu lửa
#define STT_PREHEAT_HEATING         27  // Đang tăng nhiệt đến nhiệt độ mục tiêu
#define STT_PREHEAT_HOLDING         28  // Đang giữ nhiệt tại nhiệt độ mục tiêu
#define STT_PREHEAT_3MIN_WARN       29  // Đã hết 3 phút nhưng BT chưa đạt nhiệt độ mục tiêu
#define STT_PREHEAT_DONE            30  // Làm nóng máy rang hoàn tất, hết thời gian cài đặt
#define STT_PREHEAT_CANCELLED       31  // Người dùng hủy làm nóng máy rang giữa chừng
#define STT_PREHEAT_TIMEOUT         32  // Làm nóng máy rang hết tổng thời gian cho phép
#define STT_PREHEAT_BT_NO_RISE      33  // Nhiệt độ BT không tăng dù 60 giây trong khi ET đang tăng
#define STT_PREHEAT_BT_SENSOR_ERR   34  // Cảm biến BT không phản ứng sau 120 giây, kiểm tra ngay
#define STT_PREHEAT_AIR_RETAIN      35  // Giảm tốc độ gió để giữ nhiệt (đầu đốt đã đạt công suất tối đa)
#define STT_PREHEAT_AIR_DUMP        36  // Tăng tốc độ gió để xả bớt nhiệt (đầu đốt đã về 0%)
#define STT_PREHEAT_OVERSHOOT       37  // Nhiệt độ BT vượt quá mức mục tiêu trong lúc làm nóng
#define STT_PREHEAT_FF_LEARNED      38  // Bảng học tự động: đã học được mức lửa cho vùng nhiệt này
#define STT_PREHEAT_FF_LOADED       39  // Đã tải bảng học tự động làm nóng từ thẻ nhớ SD
#define STT_PREHEAT_FF_SAVED        40  // Đã lưu bảng học tự động làm nóng vào thẻ nhớ SD
#define STT_PREHEAT_THERMAL_COLD    41  // Phát hiện trống rang còn nguội (ET thấp hơn BT)
#define STT_PREHEAT_THERMAL_HOT     42  // Phát hiện trống rang đã nóng (ET cao hơn BT)
#define STT_PREHEAT_GAIN_LEARNED    43  // Đã học hệ số phản ứng đầu đốt cho vùng nhiệt này
#define STT_PREHEAT_COOLING_DONE    44  // Giai đoạn làm nguội xong, chuẩn bị bật đầu đốt
#define STT_PREHEAT_COAST           45  // Đang chờ ET và BT hội tụ sau khi làm nguội
#define STT_PREHEAT_PRE_IGNITE      46  // Thổi sạch buồng đốt trước khi mồi lửa
#define STT_PREHEAT_PRECISION       47  // Chế độ chính xác cuối: PI khử offset, giữ target ±1°C
#define STT_PREHEAT_INVARIANT_FAIL  48  // CẢNH BÁO: state invariant bị vi phạm, force về giá trị an toàn
#define STT_PREHEAT_GAS_LOST        49  // Tín hiệu lửa mất giữa giai đoạn đốt, đang retry mồi lại
#define STT_PREHEAT_SENSOR_DROP     50  // CẢNH BÁO: cảm biến BT/ET nhảy bất thường > 50°C/5s

// [51-80] Bước rang (progStep)
#define STT_ROAST_IDLE              51  // Chương trình rang chưa chạy
#define STT_ROAST_INIT              52  // Đang reset dữ liệu, chuẩn bị cho mẻ rang mới
#define STT_ROAST_COOLDOWN          53  // Chờ BT nguội xuống để chuẩn bị bật lại đầu đốt
#define STT_ROAST_WAITGAS           54  // Chờ tín hiệu lửa từ đầu đốt
#define STT_ROAST_CHECK             55  // Cho BT dat nhiet do charge, sap bat charge cylinder
#define STT_ROAST_WAIT_CHARGE       56  // Cho thao tac charge vao trong
#define STT_ROAST_CATCH_TP          57  // Dang cho TP reached: giai doan tu charge den TP
#define STT_ROAST_YELLOW            58  // Dang cho Yellow reached
#define STT_ROAST_FCS               59  // Dang cho FCs reached
#define STT_ROAST_DEV               60  // Dang trong giai doan Dev
#define STT_ROAST_DROP              61  // Dang xa lieu bang drop cylinder
#define STT_ROAST_COOLING           62  // Mix&Cool: mixer va cooling dang chay
#define STT_ROAST_ESCAPE            63  // Dang xa khi bang escape cylinder
#define STT_ROAST_LOOP1             64  // Trạng thái vòng lặp 1
#define STT_ROAST_LOOP2             65  // Trạng thái vòng lặp 2
#define STT_ROAST_AUTO_MODE         66  // Chế độ rang tự động theo hồ sơ đang chạy
#define STT_ROAST_SAVE_MODE         67  // Chế độ rang thủ công (ghi hồ sơ) đang chạy

// [81-100] Sự kiện rang
#define STT_EVENT_TP_REACHED        81  // TP reached
#define STT_EVENT_YELLOW_REACHED    82  // Yellow reached
#define STT_EVENT_FCS_REACHED       83  // FCs reached
#define STT_EVENT_DEV_REACHED       84  // Bat dau giai doan Dev
#define STT_EVENT_DROP_REACHED      85  // Drop reached
#define STT_EVENT_CHARGE_OPENED     86  // Charge cylinder opened
#define STT_EVENT_CHARGE_CLOSED     87  // Charge cylinder closed
#define STT_EVENT_DROP_OPENED       88  // Drop cylinder opened
#define STT_EVENT_DROP_CLOSED       89  // Drop cylinder closed
#define STT_EVENT_ESCAPE_OPENED     90  // Escape cylinder opened
#define STT_EVENT_ESCAPE_CLOSED     91  // Escape cylinder closed
#define STT_EVENT_GAS_CALIB         92  // Đang tự động hiệu chỉnh mức lửa theo nhiệt độ
#define STT_EVENT_ROR_CTRL_ON       93  // Bộ điều khiển tốc độ tăng nhiệt đang điều chỉnh lửa
#define STT_EVENT_ROAST_START       94  // Đồng hồ rang bắt đầu đếm giờ
#define STT_EVENT_ROAST_END         95  // Kết thúc quá trình rang

// [101-120] Thẻ nhớ SD / hồ sơ rang
#define STT_SD_LOADING_PROFILE      101 // Đang tải hồ sơ rang từ thẻ nhớ SD
#define STT_SD_LOAD_OK              102 // Tải hồ sơ rang thành công
#define STT_SD_LOAD_FAIL            103 // Tải hồ sơ thất bại (file hỏng hoặc không có)
#define STT_SD_SAVING_PROFILE       104 // Đang lưu hồ sơ rang vào thẻ nhớ SD
#define STT_SD_SAVE_OK              105 // Lưu hồ sơ rang thành công
#define STT_SD_SAVE_FAIL            106 // Lưu hồ sơ rang thất bại
#define STT_SD_DELETING_PROFILE     107 // Đang xóa một hồ sơ rang
#define STT_SD_DELETE_OK            108 // Xóa hồ sơ rang thành công
#define STT_SD_DELETE_FAIL          109 // Xóa hồ sơ rang thất bại
#define STT_SD_DELETING_ALL         110 // Đang xóa tất cả hồ sơ rang
#define STT_SD_LOG_STARTED          111 // Bắt đầu ghi dữ liệu rang ra file CSV
#define STT_SD_LOG_WRITING          112 // Đang ghi dữ liệu rang theo từng giây
#define STT_SD_LOG_ENDED            113 // Kết thúc ghi dữ liệu rang
#define STT_SD_PID_FF_LOADED        114 // Đã tải bảng học điều áp hút từ /pid_ff.txt
#define STT_SD_PID_FF_SAVED         115 // Đã lưu bảng học điều áp hút vào /pid_ff.txt
#define STT_SD_PH_FF_LOADED         116 // Đã tải bảng học làm nóng từ /ph_ff.txt
#define STT_SD_PH_FF_SAVED          117 // Đã lưu bảng học làm nóng vào /ph_ff.txt
#define STT_SD_PROFILE_SELECTED     118 // Người dùng đã chọn số hiệu hồ sơ
#define STT_SD_PROFILE_DATE_LOADED  119 // Đã quét ngày giờ tất cả hồ sơ lên màn hình HMI
#define STT_SD_LOAD_NO_FILE         120 // Load profile fail: no .csv or .txt file

// [121-140] Điều áp hút / chỉnh tốc độ gió tự động
#define STT_PID_NORMAL              121 // Bộ điều áp hút đang hoạt động bình thường
#define STT_PID_STEP_UP             122 // Tốc độ gió tăng 1 bước (áp hút quá thấp)
#define STT_PID_STEP_DOWN           123 // Tốc độ gió giảm 1 bước (áp hút quá cao)
#define STT_PID_SNAP                124 // Tốc độ gió nhảy nhanh đến giá trị trong bảng học
#define STT_PID_FF_LEARNED          125 // Bảng học điều áp hút: thêm mục mới đã học
#define STT_PID_FF_UPDATED          126 // Bảng học điều áp hút: cập nhật mục hiện có
#define STT_PID_FF_FULL             127 // Bảng học điều áp hút đầy (tối đa 50 mục)
#define STT_PID_TUNE_START          128 // Bắt đầu quá trình tự động chỉnh điều áp hút
#define STT_PID_TUNE_WARMUP         129 // Đang chờ 15 giây trước khi quét tốc độ gió
#define STT_PID_TUNE_RUNNING        130 // Đang quét tốc độ gió từ 0 đến 100% từng bước 1%
#define STT_PID_TUNE_DONE           131 // Chỉnh điều áp hút hoàn tất, đã lưu kết quả vào SD
#define STT_PID_TUNE_ABORTED        132 // Người dùng hủy quá trình chỉnh điều áp hút giữa chừng
#define STT_PID_VACUUM_RESET        133 // Bộ điều áp hút khởi động lại do giá trị đặt thay đổi
#define STT_PID_VACUUM_CLAMPED      134 // Giá trị đặt áp hút bị giới hạn trong khoảng 90-250 Pa
#define STT_PID_DISABLED            135 // Bộ điều áp hút đã tắt, điều khiển tốc độ gió trực tiếp
#define STT_PID_ENABLED             136 // Bộ điều áp hút đã bật

// [141-160] Sự kiện màn hình HMI / điều khiển từ máy tính
#define STT_HMI_START_PRESSED       141 // Người dùng bấm nút Bắt đầu trên màn hình HMI
#define STT_HMI_GAS_PRESSED         142 // Người dùng bấm nút bật/tắt đầu đốt
#define STT_HMI_CHARGE_PRESSED      143 // Người dùng bấm nút nạp liệu vào trống rang
#define STT_HMI_DROP_PRESSED        144 // Người dùng bấm nút xả liệu ra ngoài
#define STT_HMI_ESCAPE_PRESSED      145 // Người dùng bấm nút xả khí
#define STT_HMI_COOLING_PRESSED     146 // Người dùng bấm nút làm nguội
#define STT_HMI_FEEDER_PRESSED      147 // Người dùng bấm nút máy cấp liệu
#define STT_HMI_DESTONER_PRESSED    148 // Người dùng bấm nút máy tách đá
#define STT_HMI_AB_PRESSED          149 // Người dùng bấm nút buồng đốt khí thải
#define STT_HMI_SAVE_PRESSED        150 // Người dùng bấm nút lưu hồ sơ rang
#define STT_HMI_PREHEAT_PRESSED     151 // Người dùng bấm nút làm nóng máy rang
#define STT_HMI_PC_CMD_IGNITION     152 // Máy tính (Artisan) gửi lệnh bật đầu đốt
#define STT_HMI_PC_CMD_CHARGE       153 // Máy tính (Artisan) gửi lệnh nạp liệu
#define STT_HMI_PC_CMD_DROP         154 // Máy tính (Artisan) gửi lệnh xả liệu
#define STT_HMI_PC_CMD_ESCAPE       155 // Máy tính (Artisan) gửi lệnh xả khí
#define STT_HMI_PC_CMD_COOL         156 // Máy tính (Artisan) gửi lệnh làm nguội
#define STT_HMI_SV_UPDATED          157 // Giá trị đặt nhiệt độ BT được cập nhật từ HMI hoặc máy tính
#define STT_HMI_VACUUM_SV_UPDATED   158 // Giá trị đặt áp hút được cập nhật
#define STT_HMI_PARAM_UPDATED       159 // Một thông số cài đặt ($M) đã thay đổi
#define STT_HMI_RELOAD_PROFILE      160 // Yêu cầu tải lại danh sách hồ sơ từ thẻ nhớ SD

// [161-180] Đầu đốt / gió / trống rang
#define STT_GAS_ON                  161 // Rơ le đầu đốt đã bật, đang cháy
#define STT_GAS_OFF                 162 // Rơ le đầu đốt đã tắt, không cháy
#define STT_GAS_SIGNAL_OK           163 // Nhận được tín hiệu lửa (cảm biến xác nhận có lửa)
#define STT_GAS_SIGNAL_LOST         164 // Mất tín hiệu lửa (lửa bị tắt đột ngột)
#define STT_GAS_SLEW_RISING         165 // Mức lửa đang tăng dần (giới hạn tốc độ tăng)
#define STT_GAS_SLEW_FALLING        166 // Mức lửa đang giảm dần (giới hạn tốc độ giảm)
#define STT_GAS_CLAMPED_MAX         167 // Mức lửa bị giới hạn bởi ngưỡng tối đa trên HMI
#define STT_GAS_SOURCE_VR           168 // Mức lửa điều khiển từ biến trở tay (thủ công)
#define STT_GAS_SOURCE_PC           169 // Mức lửa điều khiển từ phần mềm máy tính (Artisan)
#define STT_GAS_SOURCE_AUTO         170 // Mức lửa điều khiển tự động theo hồ sơ rang
#define STT_GAS_SOURCE_PREHEAT      171 // Mức lửa điều khiển bởi hệ thống làm nóng máy
#define STT_DRUM_ON                 172 // Rơ le trống rang đã bật
#define STT_DRUM_OFF                173 // Rơ le trống rang đã tắt
#define STT_DRUM_SPEED_UPDATED      174 // Tốc độ trống rang đã ghi thành công vào biến tần
#define STT_AIR_SOURCE_VR           175 // Tốc độ gió điều khiển từ biến trở tay (thủ công)
#define STT_AIR_SOURCE_PC           176 // Tốc độ gió điều khiển từ phần mềm máy tính (Artisan)
#define STT_AIR_SOURCE_AUTO         177 // Tốc độ gió điều khiển bởi bộ điều áp hút tự động
#define STT_AIR_SOURCE_PREHEAT      178 // Tốc độ gió điều khiển bởi hệ thống làm nóng máy

// [201-220] Cơ cấu chấp hành (xi lanh, rơ le)
#define STT_ACT_CHARGE_OPEN         201 // Charge cylinder opened
#define STT_ACT_CHARGE_CLOSED       202 // Charge cylinder closed
#define STT_ACT_CHARGE_TIMER_ON     203 // Auto-close timer for charge cylinder is running
#define STT_ACT_DROP_OPEN           204 // Drop cylinder opened
#define STT_ACT_DROP_CLOSED         205 // Drop cylinder closed
#define STT_ACT_DROP_TIMER_ON       206 // Auto-close timer for drop cylinder is running
#define STT_ACT_ESCAPE_OPEN         207 // Escape cylinder opened
#define STT_ACT_ESCAPE_CLOSED       208 // Escape cylinder closed
#define STT_ACT_ESCAPE_TIMER_ON     209 // Auto-close timer for escape cylinder is running
#define STT_ACT_COOLING_ON          210 // Mix&Cool started
#define STT_ACT_COOLING_OFF         211 // Mix&Cool stopped
#define STT_ACT_COOLING_TIMER_ON    212 // Mix&Cool timer is running
#define STT_ACT_AB_ON               213 // Rơ le buồng đốt khí thải đã bật
#define STT_ACT_AB_OFF              214 // Rơ le buồng đốt khí thải đã tắt
#define STT_ACT_AB_WAIT             215 // Buồng đốt khí thải đang chờ delay trước khi bật
#define STT_ACT_DISCHARGE_ON        216 // Xi lanh xả dài đã mở
#define STT_ACT_DISCHARGE_OFF       217 // Xi lanh xả dài đã đóng

// [221-240] Hệ thống cấp liệu / tách đá / nạp liệu tự động
#define STT_FEEDER_ON               221 // Máy cấp liệu đã bật
#define STT_FEEDER_OFF              222 // Máy cấp liệu đã tắt
#define STT_FEEDER_TIMER_ON         223 // Bộ đếm thời gian máy cấp liệu đang chạy
#define STT_FEEDER_CLEAN_ON         224 // Chu kỳ vệ sinh máy cấp liệu đang chạy
#define STT_DESTONER_ON             225 // Máy tách đá đã bật
#define STT_DESTONER_OFF            226 // Máy tách đá đã tắt
#define STT_DESTONER_TIMER_ON       227 // Bộ đếm thời gian máy tách đá đang chạy
#define STT_LOADER_IDLE             228 // Bộ nạp liệu tự động đang nghỉ
#define STT_LOADER_RUNNING          229 // Bộ nạp liệu tự động đang hoạt động
#define STT_LOADER_WAITING          230 // Bộ nạp liệu đang chờ đạt trọng lượng mục tiêu
#define STT_LOADER_OK               231 // Bộ nạp liệu: đã đạt trọng lượng mục tiêu
#define STT_LOADER_FAIL             232 // Bộ nạp liệu: thất bại hoặc hết thời gian chờ
#define STT_AUTOFILL_ON             233 // Hệ thống tự động đổ đầy thùng chứa đã bật
#define STT_AUTOFILL_OFF            234 // Hệ thống tự động đổ đầy thùng chứa đã tắt
#define STT_AUTOFILL_TIMER_ON       235 // Bộ đếm tự động đổ đầy thùng chứa đang chạy

// [241-260] Cân / trọng lượng sản phẩm
#define STT_SCALE_DATA_OK           241 // Dữ liệu cân hợp lệ, đã nhận thành công
#define STT_SCALE_DATA_INVALID      242 // Dữ liệu cân không hợp lệ (lỗi đọc hoặc phân tích)
#define STT_SCALE_NEGATIVE          243 // Cân đọc giá trị âm (có thể chưa đặt zero)
#define STT_SCALE_THRESHOLD_HIGH    244 // Trọng lượng vượt qua ngưỡng cao
#define STT_SCALE_THRESHOLD_MED     245 // Trọng lượng vượt qua ngưỡng trung bình
#define STT_SCALE_THRESHOLD_LOW     246 // Trọng lượng vượt qua ngưỡng thấp
#define STT_SCALE_TOLERANCE_HIGH    247 // Trọng lượng nằm trong sai số cho phép mức cao
#define STT_SCALE_TOLERANCE_MED     248 // Trọng lượng nằm trong sai số cho phép mức trung
#define STT_SCALE_TOLERANCE_LOW     249 // Trọng lượng nằm trong sai số cho phép mức thấp

// [261-280] Cảnh báo cảm biến / nhiệt độ
#define STT_TEMP_BT_OK              261 // Nhiệt độ BT đang ở mức bình thường
#define STT_TEMP_ET_OK              262 // Nhiệt độ ET đang ở mức bình thường
#define STT_TEMP_BT_HIGH            263 // NGUY HIỂM: Nhiệt độ BT vượt 250°C — đã tắt lửa
#define STT_TEMP_ET_HIGH            264 // NGUY HIỂM: Nhiệt độ ET vượt 350°C — đã tắt lửa
#define STT_TEMP_BT_INVALID         265 // Không đọc được nhiệt độ BT (giá trị 0 hoặc bất thường)
#define STT_TEMP_ET_INVALID         266 // Không đọc được nhiệt độ ET (giá trị 0 hoặc bất thường)
#define STT_TEMP_DIVERGENCE         267 // Nhiệt độ BT và ET lệch nhau quá lớn (có thể lỗi cảm biến)
#define STT_VACUUM_HIGH             268 // Áp hút vượt quá ngưỡng tối đa (maxPT)
#define STT_VACUUM_LOW              269 // Áp hút dưới ngưỡng tối thiểu (minPT)
#define STT_THERMAL_ACCUMULATION    270 // Trống rang đang tích nhiệt (BT không tăng dù ET tăng)
#define STT_TEMP_BT_SENSOR_ERR      271 // Cảm biến BT không phản ứng sau 120 giây, kiểm tra ngay
#define STT_TEMP_ROR_STALL          272 // Tốc độ tăng nhiệt BT bị kẹt, không thay đổi
#define STT_TEMP_BT_OVERSHOOT       273 // Nhiệt độ BT vượt quá mức mục tiêu trong lúc làm nóng hoặc rang

// [281-300] Lỗi truyền thông Modbus
#define STT_MB_HMI_ERROR            281 // Lỗi kết nối Modbus với màn hình HMI
#define STT_MB_BT_ERROR             282 // Lỗi kết nối Modbus với cảm biến nhiệt BT
#define STT_MB_ET_ERROR             283 // Lỗi kết nối Modbus với cảm biến nhiệt ET
#define STT_MB_DRUM_ERROR           284 // Lỗi kết nối Modbus với biến tần điều khiển trống
#define STT_MB_AIR_ERROR            285 // Lỗi kết nối Modbus với biến tần điều khiển tốc độ gió
#define STT_MB_RELAY_ERROR          286 // Lỗi kết nối Modbus với bộ rơ le IO
#define STT_MB_VACUUM_ERROR         287 // Lỗi kết nối Modbus với cảm biến áp hút
#define STT_MB_CRC_ERROR            288 // Lỗi kiểm tra CRC gói tin Modbus (dữ liệu bị nhiễu)
#define STT_MB_TIMEOUT              289 // Hết thời gian chờ phản hồi từ thiết bị Modbus
#define STT_MB_WRONG_ID             290 // Nhận phản hồi từ sai ID thiết bị
#define STT_MB_FUNC_ERROR           291 // Mã hàm Modbus không được thiết bị hỗ trợ
#define STT_MB_ADDR_ERROR           292 // Địa chỉ thanh ghi Modbus yêu cầu không hợp lệ
#define STT_MB_DATA_ERROR           293 // Giá trị dữ liệu Modbus gửi đi không hợp lệ
#define STT_MB_SLAVE_FAIL           294 // Thiết bị Modbus báo lỗi xử lý nội bộ
#define STT_MB_HMI_RESET_FAIL       295 // Lệnh khởi động lại màn hình HMI không thành công
#define STT_MB_DRUM_WRITE_FAIL      296 // Ghi tốc độ trống vào biến tần thất bại
#define STT_MB_AIR_WRITE_FAIL       297 // Ghi tốc độ gió vào biến tần thất bại

// [301-320] Kết quả kiểm tra khi khởi động máy
#define STT_STARTUP_CHECK_HMI       301 // Đang kiểm tra kết nối màn hình HMI
#define STT_STARTUP_HMI_OK          302 // Màn hình HMI kết nối thành công
#define STT_STARTUP_HMI_FAIL        303 // Màn hình HMI THẤT BẠI — kiểm tra cáp kết nối
#define STT_STARTUP_CHECK_BT        304 // Đang kiểm tra cảm biến nhiệt độ BT
#define STT_STARTUP_BT_OK           305 // Cảm biến nhiệt BT kết nối thành công
#define STT_STARTUP_BT_FAIL         306 // Cảm biến nhiệt BT THẤT BẠI — kiểm tra cáp RS485
#define STT_STARTUP_CHECK_ET        307 // Đang kiểm tra cảm biến nhiệt độ ET
#define STT_STARTUP_ET_OK           308 // Cảm biến nhiệt ET kết nối thành công
#define STT_STARTUP_ET_FAIL         309 // Cảm biến nhiệt ET THẤT BẠI — kiểm tra cáp RS485
#define STT_STARTUP_CHECK_AIR       310 // Đang kiểm tra biến tần điều khiển tốc độ gió
#define STT_STARTUP_AIR_OK          311 // Biến tần tốc độ gió kết nối thành công
#define STT_STARTUP_AIR_FAIL        312 // Biến tần tốc độ gió THẤT BẠI — kiểm tra cáp RS485
#define STT_STARTUP_CHECK_DRUM      313 // Đang kiểm tra biến tần điều khiển trống rang
#define STT_STARTUP_DRUM_OK         314 // Biến tần trống rang kết nối thành công
#define STT_STARTUP_DRUM_FAIL       315 // Biến tần trống rang THẤT BẠI — kiểm tra cáp RS485
#define STT_STARTUP_CHECK_RELAY     316 // Đang kiểm tra bộ rơ le IO
#define STT_STARTUP_RELAY_OK        317 // Bộ rơ le IO kết nối thành công
#define STT_STARTUP_RELAY_FAIL      318 // Bộ rơ le IO THẤT BẠI — kiểm tra cáp RS485
#define STT_STARTUP_CHECK_SD        319 // Đang kiểm tra thẻ nhớ SD
#define STT_STARTUP_SD_OK           320 // Thẻ nhớ SD kết nối và hoạt động tốt

// [321-350] Trạng thái bộ điều khiển tốc độ tăng nhiệt
#define STT_ROR_CTRL_IDLE           321 // Bộ điều khiển tốc độ tăng nhiệt chưa kích hoạt
#define STT_ROR_CTRL_ACTIVE         322 // Bộ điều khiển tốc độ tăng nhiệt đang hoạt động
#define STT_ROR_CTRL_STEP_UP        323 // Tăng mức lửa để đẩy nhanh tốc độ tăng nhiệt
#define STT_ROR_CTRL_STEP_DOWN      324 // Giảm mức lửa để làm chậm tốc độ tăng nhiệt
#define STT_ROR_CTRL_DEAD_TIME      325 // Đang chờ hệ thống ổn định sau khi điều chỉnh lửa
#define STT_ROR_ET_LEADING          326 // ET đang tăng trước BT (trễ bình thường 5-15 giây)
#define STT_ROR_BT_STALL            327 // Tốc độ tăng nhiệt BT bị kẹt, đã tăng lửa để phục hồi
#define STT_ROR_OVERSHOOT_WARN      328 // Dự báo: nhiệt độ BT sẽ vượt quá mức mục tiêu
#define STT_ROR_DECEL_HOLD          329 // Tốc độ tăng nhiệt đang giảm, giữ lửa cho hệ thống ổn định
#define STT_ROR_CRASH_WARN          330 // CẢNH BÁO: Tốc độ tăng nhiệt BT đang giảm mạnh đột ngột

// [351-380] Học nhiệt / bảng học tự động làm nóng
#define STT_PH_FF_COLD_LEARNED      351 // Đã học mức lửa khi trống rang nguội cho vùng nhiệt này
#define STT_PH_FF_HOT_LEARNED       352 // Đã học mức lửa khi trống rang nóng cho vùng nhiệt này
#define STT_PH_FF_GAIN_UPDATED      353 // Hệ số phản ứng đầu đốt đã được cập nhật cho vùng nhiệt
#define STT_PH_COOL_AIRFLOW_UP      354 // Làm nguội: tăng tốc độ gió để hút nhiệt ra ngoài
#define STT_PH_COOL_AIRFLOW_DOWN    355 // Làm nguội: giảm tốc độ gió vì đang nguội quá nhanh
#define STT_PH_HEAT_GAS_UP          356 // Tăng nhiệt: tăng mức lửa vì tốc độ tăng nhiệt quá chậm
#define STT_PH_HEAT_GAS_DOWN        357 // Tăng nhiệt: giảm mức lửa vì tốc độ tăng nhiệt quá nhanh
#define STT_PH_HEAT_AIR_RETAIN      358 // Tăng nhiệt: giảm tốc độ gió để giữ nhiệt (lửa đã tối đa)
#define STT_PH_HEAT_AIR_DUMP        359 // Tăng nhiệt: tăng tốc độ gió để xả nhiệt dư (lửa đã về 0%)
#define STT_PH_HOLD_GAS_ADJ         360 // Giữ nhiệt: điều chỉnh mức lửa để nhiệt độ BT ổn định
#define STT_PH_HOLD_AIR_ADJ         361 // Giữ nhiệt: điều chỉnh tốc độ gió để hỗ trợ ổn định nhiệt
#define STT_PH_STABLE               362 // Nhiệt độ BT ổn định tại mức mục tiêu, đang ghi nhớ dữ liệu
#define STT_PH_VACUUM_SAVED         363 // Đã lưu trạng thái bộ điều áp hút trước khi làm nóng máy
#define STT_PH_VACUUM_RESTORED      364 // Đã khôi phục trạng thái bộ điều áp hút sau khi tắt làm nóng

// [381-385] Chi tiet loi load profile SD
#define STT_SD_LOAD_BAD_CHARGE      381 // Load profile fail: missing/invalid CHARGE BT
#define STT_SD_LOAD_BAD_TP          382 // Load profile fail: missing TP
#define STT_SD_LOAD_BAD_DROP_TIME   383 // Load profile fail: missing DROP or roast time too short
#define STT_SD_LOAD_BAD_DROP_TEMP   384 // Load profile fail: missing/invalid DROP BT
#define STT_SD_LOAD_BAD_TXT         385 // Load profile fail: invalid TXT profile properties

// [401-430] Lỗi nghiêm trọng — cần xử lý ngay
#define STT_ERR_FIRE_ALARM          401 // BÁO CHÁY: Nhiệt độ BT vượt 250°C — đã tắt lửa ngay lập tức
#define STT_ERR_TEMP_RUNAWAY        402 // Nhiệt độ tăng mất kiểm soát — nguy hiểm
#define STT_ERR_GAS_FAULT           403 // Lỗi hệ thống gas — kiểm tra van và đường ống dẫn gas
#define STT_ERR_SENSOR_BT           404 // Cảm biến nhiệt BT bị lỗi nghiêm trọng — thay thế hoặc kiểm tra
#define STT_ERR_SENSOR_ET           405 // Cảm biến nhiệt ET bị lỗi nghiêm trọng — thay thế hoặc kiểm tra
#define STT_ERR_DRUM_FAULT          406 // Biến tần trống rang bị lỗi — kiểm tra nguồn điện và kết nối
#define STT_ERR_AIR_FAULT           407 // Biến tần tốc độ gió bị lỗi — kiểm tra nguồn điện và kết nối
#define STT_ERR_RELAY_FAULT         408 // Bộ rơ le IO bị lỗi — kiểm tra cáp kết nối
#define STT_ERR_SD_FAULT            409 // Thẻ nhớ SD bị lỗi — kiểm tra hoặc thay thế thẻ nhớ
#define STT_ERR_IGNITION_FAIL       410 // Bật đầu đốt thất bại 3 lần liên tiếp — kiểm tra gas và đầu đốt
#define STT_ERR_LOADER_FAULT        411 // Bộ nạp liệu tự động bị lỗi nghiêm trọng
#define STT_ERR_VACUUM_FAULT        412 // Hệ thống áp hút bị lỗi — kiểm tra cảm biến áp suất
#define STT_ERR_ROR_BT_EXTREME      413 // BÁO CHÁY: tốc độ tăng nhiệt BT > 500°C/min — đã tắt lửa

// Tổng cộng: ~380 mã trạng thái, bắt đầu từ 1

// ── Biến trạng thái (dùng chung) ─────────────────────────────────────────────
static uint16_t sttQueue[10];
static uint8_t  sttQHead = 0;
static uint8_t  sttQTail = 0;
static uint8_t  sttQCount = 0;
static uint16_t sttLastSent = 0;
static uint32_t sttLastFlushMs = 0;

// Whitelist: chỉ các mã trong danh sách này mới hiển thị lên HMI cho người vận hành
// Mã nội bộ / học tự động / kỹ thuật bị lọc bỏ
inline bool sttIsOperatorVisible(uint16_t code) {
    if (code == 1) return true;
    if (code == 2 || code == 3 || code == 8 || code == 9 || code == 11) return true;
    if (code >= 21 && code <= 44) {
        if (code == 22 || code == 24 || code == 35 || code == 36 ||
            (code >= 38 && code <= 43)) return false;
        return true;
    }
    if (code >= 51 && code <= 67) {
        if (code == 51 || code == 53 || code == 54 || code == 56 ||
            code == 64 || code == 65) return false;
        return true;
    }
    if (code >= 81 && code <= 95) {
        if (code == 92 || code == 93) return false;
        return true;
    }
    if (code >= 101 && code <= 120) {
        if (code == 111 || code == 112 || code == 113 ||
            code == 114 || code == 115 || code == 116 || code == 117 ||
            code == 119) return false;
        return true;
    }
    if (code >= 121 && code <= 136) {
        if (code == 122 || code == 123 || code == 124 || code == 125 ||
            code == 126 || code == 127 || code == 129 || code == 133 || code == 134)
            return false;
        return true;
    }
    if (code >= 141 && code <= 160) return false;
    if (code >= 161 && code <= 178) {
        if (code == 165 || code == 166 || code == 167 || code == 174) return false;
        return true;
    }
    if (code >= 201 && code <= 217) {
        if (code == 203 || code == 206 || code == 209 || code == 212 || code == 215)
            return false;
        return true;
    }
    if (code >= 221 && code <= 235) {
        if (code == 223 || code == 224 || code == 227 || code == 230 || code == 235)
            return false;
        return true;
    }
    if (code >= 241 && code <= 249) {
        if (code == 242 || code == 243) return false;
        return true;
    }
    if (code >= 261 && code <= 273) {
        if (code == 270) return false;
        return true;
    }
    if (code >= 281 && code <= 297) {
        if (code >= 288) return false;
        return true;
    }
    if (code >= 301 && code <= 320) {
        if (code == 301 || code == 304 || code == 307 || code == 310 ||
            code == 313 || code == 316 || code == 319) return false;
        return true;
    }
    if (code >= 321 && code <= 330) {
        if (code >= 323 && code <= 328) return false;
        return true;
    }
    if (code >= 351 && code <= 364) {
        if (code >= 351 && code <= 361) return false;
        return true;
    }
    if (code >= 381 && code <= 385) return true;
    if (code >= 401 && code <= 412) return true;
    return false;
}

// Đẩy mã trạng thái vào hàng đợi (không chặn, bỏ mã cũ nhất nếu đầy)
// Mã không trong whitelist bị lọc bỏ hoàn toàn
inline void setMachineStatus(uint16_t code) {
    if (!sttIsOperatorVisible(code)) return;
    if (code == sttLastSent) return;
    if (sttQCount >= 10) {
        sttQTail = (sttQTail + 1) % 10;
        sttQCount--;
    }
    sttQueue[sttQHead] = code;
    sttQHead = (sttQHead + 1) % 10;
    sttQCount++;
}

// Ghi 1 mã lên HMI mỗi 1000ms — gọi từ rwHMI_2() trong vòng lặp chính
inline void flushMachineStatus() {
    if (sttQCount == 0) return;
    if ((uint32_t)(millis() - sttLastFlushMs) < 1000) return;
    uint16_t code = sttQueue[sttQTail];
    sttQTail      = (sttQTail + 1) % 10;
    sttQCount--;
    sttLastSent   = code;
    sttLastFlushMs = millis();
    nodeHMI.writeSingleRegister(STT_W - 1, code);
    if (enDebug) {
        SerialComputer.print("STT="); SerialComputer.println(code);
    }
}

inline void updateMachineStatus() { flushMachineStatus(); }
