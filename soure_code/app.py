import os
import struct
import heapq
import random
from flask import Flask, request, render_template, send_file, jsonify

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

FLOAT_FORMAT = 'd'
FLOAT_SIZE = struct.calcsize(FLOAT_FORMAT)

def external_sort(input_path, output_path, ram_size, num_files, skip_visualization=False):
    """
    Thực thi thuật toán Sắp xếp ngoại (Kết hợp Repacking và Multi-Pass K-Way Merge).

    Parameters:
        input_path (str): Đường dẫn tới tập tin nhị phân nguồn cần sắp xếp.
        output_path (str): Đường dẫn lưu tập tin nhị phân kết quả.
        ram_size (int): Sức chứa tối đa của RAM (số lượng phần tử được nạp cùng lúc).
        num_files (int): Số lượng tập tin tạm tối đa được phép mở đồng thời.
        skip_visualization (bool): Bật cờ này (True) để bỏ qua việc chụp ảnh UI, tối ưu tốc độ cho file lớn.

    Returns:
        tuple: (logs, frames)
            - logs (list of str): Nhật ký hệ thống ghi lại các bước xử lý (dùng để in log text).
            - frames (list of dict): Cuộn phim chứa trạng thái RAM/Disk theo từng bước (dùng cho Web Visualizer).
    """

    logs = []
    frames = [] 
    
    min_heap = []
    current_run_id = 0
    last_written = float('-inf')
    
    temp_filenames = [os.path.join(UPLOAD_FOLDER, f"temp_{i}.bin") for i in range(num_files)]
    write_handles = [open(f, 'wb') for f in temp_filenames]
    file_offsets = [0] * num_files 
    
    runs_metadata = [{'id': 0, 'file_idx': 0, 'offset': 0, 'length': 0, 'elements_read': 0, 'data_cache': []}]
    
    all_files_runs = [[] for _ in range(num_files)] 
    current_run_data = []

    def capture_frame(msg, phase):
        """
        Hàm nội bộ: Chụp lại frame trạng thái của RAM và Disk tại thời điểm gọi.
        
        Parameters:
            msg (str): Lời thoại giải thích hành động đang diễn ra tại khung hình này.
            phase (str): Tên giai đoạn ("PHASE_1", "PHASE_2", "PHASE_2_FINAL").
        """

        if skip_visualization: return 
        
        active = [round(x[1], 2) for x in min_heap if x[0] == current_run_id]
        frozen = [round(x[1], 2) for x in min_heap if x[0] > current_run_id]
        
        current_files_state = [[run.copy() for run in f_runs] for f_runs in all_files_runs]
        if phase == "PHASE_1":
            target_f_idx = current_run_id % num_files
            current_files_state[target_f_idx].append(current_run_data.copy())
            
        frames.append({
            'phase': phase, 'msg': msg, 'active': active, 'frozen': frozen,
            'files_state': current_files_state
        })

    logs.append(f"--- BẮT ĐẦU GIAI ĐOẠN 1 (RAM = {ram_size}, SỐ FILE TẠM = {num_files}) ---")
    
    with open(input_path, 'rb') as f_in:
        for _ in range(ram_size):
            bytes_read = f_in.read(FLOAT_SIZE)
            if not bytes_read: break
            val = struct.unpack(FLOAT_FORMAT, bytes_read)[0]
            heapq.heappush(min_heap, (current_run_id, val))
            
        if not min_heap: 
            for w in write_handles: w.close()
            return logs, frames
        
        capture_frame("Khởi tạo: Nạp đầy RAM", "PHASE_1")

        while min_heap:
            run_id, val = heapq.heappop(min_heap)

            if run_id > current_run_id:
                logs.append(f"--> Hoàn tất Run {current_run_id} (Dài {runs_metadata[current_run_id]['length']} số | Tại File {runs_metadata[current_run_id]['file_idx']})")
                
                if not skip_visualization: 
                    all_files_runs[current_run_id % num_files].append(current_run_data.copy())
                
                current_run_id = run_id
                target_file_idx = current_run_id % num_files
                runs_metadata.append({
                    'id': current_run_id,
                    'file_idx': target_file_idx, 'offset': file_offsets[target_file_idx],
                    'length': 0, 'elements_read': 0, 'data_cache': []
                })
                
                current_run_data = []
                capture_frame(f"Rã đông RAM - Bắt đầu Run {current_run_id}", "PHASE_1")

            curr_meta = runs_metadata[current_run_id]
            f_idx = curr_meta['file_idx']
            
            write_handles[f_idx].write(struct.pack(FLOAT_FORMAT, val))
            curr_meta['length'] += 1
            file_offsets[f_idx] += FLOAT_SIZE 
            last_written = val
            
            if not skip_visualization: 
                current_run_data.append(round(val, 2))
                curr_meta['data_cache'].append(round(val, 2))

            bytes_read = f_in.read(FLOAT_SIZE)
            
            if bytes_read:
                next_val = struct.unpack(FLOAT_FORMAT, bytes_read)[0]
                next_run_id = current_run_id
                
                if next_val < last_written:
                    next_run_id += 1 
                    msg = f"Ghi {round(val,2)}. Đọc {round(next_val,2)} -> ĐÓNG BĂNG"
                else:
                    msg = f"Ghi {round(val,2)}. Đọc {round(next_val,2)} -> HOẠT ĐỘNG"
                
                heapq.heappush(min_heap, (next_run_id, next_val))
                capture_frame(msg, "PHASE_1")

        logs.append(f"-> Hoàn tất Run {current_run_id} (Dài {runs_metadata[current_run_id]['length']} số | Tại File {runs_metadata[current_run_id]['file_idx']})")
        if not skip_visualization: 
            all_files_runs[current_run_id % num_files].append(current_run_data.copy())

    for w in write_handles: w.close()

    logs.append(f"\n--- BẮT ĐẦU TRỘN {len(runs_metadata)} RUNS THEO TỪNG PASS ---")
    
    current_temp_files = temp_filenames.copy()
    current_runs_meta = [r for r in runs_metadata if r['length'] > 0]
    pass_number = 1
    
    if len(current_runs_meta) == 0:
        open(output_path, 'wb').close()
        return logs, frames

    while True:
        is_final_pass = (len(current_runs_meta) <= num_files)
        run_groups = [current_runs_meta[i:i + num_files] for i in range(0, len(current_runs_meta), num_files)]
        
        if is_final_pass:
            out_file_names = [output_path]
            write_handles = [open(output_path, 'wb')]
        else:
            out_file_names = [os.path.join(UPLOAD_FOLDER, f"temp_pass{pass_number}_{i}.bin") for i in range(num_files)]
            write_handles = [open(f, 'wb') for f in out_file_names]
            
        new_runs_meta = []
        new_file_offsets = [0] * (1 if is_final_pass else num_files)
        read_handles = {f_idx: open(f, 'rb') for f_idx, f in enumerate(current_temp_files)}
        writing_files_status = [[] for _ in range(1 if is_final_pass else num_files)]
        
        for group_idx, group in enumerate(run_groups):
            merge_heap = []
            target_f_idx = 0 if is_final_pass else (group_idx % num_files)
            out_f = write_handles[target_f_idx]
            start_offset = new_file_offsets[target_f_idx]
            
            current_merged_run_data = []
            writing_files_status[target_f_idx].append(current_merged_run_data)
            
            for run_meta in group:
                rh = read_handles[run_meta['file_idx']]
                rh.seek(run_meta['offset'])
                val = struct.unpack(FLOAT_FORMAT, rh.read(FLOAT_SIZE))[0]
                run_meta['elements_read'] = 1
                heapq.heappush(merge_heap, (val, run_meta['id']))
                    
            while merge_heap:
                val, r_id = heapq.heappop(merge_heap)
                out_f.write(struct.pack(FLOAT_FORMAT, val))
                current_merged_run_data.append(round(val, 2))
                
                r_meta = next(r for r in group if r['id'] == r_id)
                
                if not skip_visualization:
                    reading_fs = []
                    for f_idx in range(len(current_temp_files)):
                        fruns = []
                        for r in current_runs_meta:
                            if r['file_idx'] == f_idx:
                                fruns.append({'data': r['data_cache'], 'read': r['elements_read']})
                        reading_fs.append({'file_idx': f_idx, 'runs': fruns})
                    
                    heap_state = [round(x[0], 2) for x in merge_heap]
                    msg = f"Pass {pass_number}: Rút {round(val,2)} từ Run cũ ghi vào " + ("File Đích" if is_final_pass else f"File Mới {target_f_idx}")
                    frames.append({
                        'phase': "PHASE_2_FINAL" if is_final_pass else "PHASE_2",
                        'msg': msg, 'active': heap_state, 'reading': reading_fs,
                        'writing': [[run.copy() for run in wf] for wf in writing_files_status] 
                    })
                
                if r_meta['elements_read'] < r_meta['length']:
                    rh = read_handles[r_meta['file_idx']]
                    read_pos = r_meta['offset'] + r_meta['elements_read'] * FLOAT_SIZE
                    rh.seek(read_pos)
                    next_val = struct.unpack(FLOAT_FORMAT, rh.read(FLOAT_SIZE))[0]
                    r_meta['elements_read'] += 1
                    heapq.heappush(merge_heap, (next_val, r_id))
                    
            new_runs_meta.append({
                'id': group_idx, 'file_idx': target_f_idx, 'offset': start_offset,
                'length': len(current_merged_run_data), 'elements_read': 0,
                'data_cache': current_merged_run_data.copy()
            })
            new_file_offsets[target_f_idx] += len(current_merged_run_data) * FLOAT_SIZE
            logs.append(f"  -> Pass {pass_number}: Tạo Run mới dài {len(current_merged_run_data)} số tại file {out_file_names[target_f_idx]}")
            
        for rh in read_handles.values(): rh.close()
        for wh in write_handles: wh.close()
        for f in current_temp_files: 
            if f != output_path: os.remove(f)
        
        current_temp_files = out_file_names
        current_runs_meta = new_runs_meta
        pass_number += 1
        
        if is_final_pass:
            break
            
    logs.append("-> Đã trộn thành công và xuất ra file đích!")
    return logs, frames

# ==========================================
# CÁC API FLASK CHO GIAO DIỆN WEB
# ==========================================

@app.route('/')
def index(): 
    """Render giao diện chính của ứng dụng."""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_random_file():
    """
    API Sinh dữ liệu ngẫu nhiên.
    Sinh ra một tập tin nhị phân chứa các số thực ngẫu nhiên từ 0.0 đến 1000.0.
    Trả về URL tải xuống tập tin vừa tạo.
    """

    try:
        num_elements = int(request.json.get('num_elements', 15))
        filename = f"random_{num_elements}_elements.bin"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        with open(filepath, 'wb') as f:
            for _ in range(num_elements): f.write(struct.pack(FLOAT_FORMAT, random.uniform(0.0, 1000.0)))
        return jsonify({'message': 'Thành công', 'download_url': f'/download/{filename}'})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    API Xử lý tập tin tải lên và kích hoạt Thuật toán Sắp xếp ngoại.
    - Nhận các thông số cấu hình: file, ram_size, num_files, is_auto_sector.
    - Tính toán tự động kích thước RAM nếu cờ Auto Sector (512B) được bật.
    - Gọi hàm `external_sort`.
    - Trả về JSON chứa Logs hệ thống và Dữ liệu Visualizer (nếu số lượng không quá 40).
    """

    if 'file' not in request.files: return jsonify({'error': 'Không tìm thấy file'}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({'error': 'Chưa chọn file'}), 400
    
    ram_size = int(request.form.get('ram_size', 3))
    num_files = int(request.form.get('num_files', 2))
    is_auto_sector = request.form.get('is_auto_sector') == 'true'

    if is_auto_sector:
        ram_size = 512 // FLOAT_SIZE  
        
    input_path = os.path.join(UPLOAD_FOLDER, file.filename)
    output_filename = f"sorted_{file.filename}"
    output_path = os.path.join(UPLOAD_FOLDER, output_filename)
    file.save(input_path)
    
    try:
        total_elements = os.path.getsize(input_path) // FLOAT_SIZE
        skip_viz = (total_elements > 40)
        
        logs, frames = external_sort(input_path, output_path, ram_size, num_files, skip_viz)
        
        if is_auto_sector:
            logs.insert(0, f"[*] CHẾ ĐỘ PHẦN CỨNG BẬT: Kích thước Sector = 512 Bytes. Dữ liệu = 8 Bytes/số.")
            logs.insert(1, f"[*] Tự động tối ưu Chunk Size (RAM) = 512 / 8 = {ram_size} phần tử/lượt đọc ghi.\n")
            
        return jsonify({
            'download_url': f'/download/{output_filename}',
            'frames': frames,
            'is_visualized': not skip_viz,
            'logs': '\n'.join(logs)
        })
    
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """
    API Cung cấp đường dẫn tải xuống tập tin tĩnh (file kết quả hoặc file sinh ngẫu nhiên).
    """
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

@app.route('/read/<filename>')
def read_binary_file(filename):
    """
    API Trích xuất dữ liệu nhị phân thành mảng số thực.
    Dùng để phục vụ tính năng "Xem Dữ Liệu Gốc / Đã Sắp Xếp" trực tiếp trên giao diện trình duyệt.
    """
    path = os.path.join(UPLOAD_FOLDER, filename)
    data = []
    try:
        with open(path, 'rb') as f:
            while True:
                bytes_read = f.read(FLOAT_SIZE)
                if not bytes_read: break
                data.append(round(struct.unpack(FLOAT_FORMAT, bytes_read)[0], 4)) 
        return jsonify({'data': data})
    except Exception as e: return jsonify({'error': str(e)}), 500

if __name__ == '__main__': app.run(debug=True, port=5000)