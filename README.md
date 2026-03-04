# 🗄️ CS523: External Sort Visualizer

Trình mô phỏng trực quan thuật toán **External Sort** xử lý trên tập tin nhị phân. 

**Sinh viên:** 24521344 - Thái Hoàng Huy Phong  

---

## 📂 Cấu trúc thư mục

Dự án được tổ chức gọn gàng với toàn bộ mã nguồn nằm trong thư mục `source_code`:

```text
📁 CS523-Assignment-1-External-Sort/
├── README.md               
└── 📁 source_code/         
    ├── requirements.txt    
    ├── app.py          
    ├── 📁 uploads/     
    └── 📁 templates/
        └── index.html      
```

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy

**Yêu cầu hệ thống:** Python 3.8+ và Trình duyệt Web hiện đại (Chrome/Edge).

**Bước 1:** Mở Terminal / PowerShell và di chuyển vào thư mục chứa mã nguồn:
```bash
cd source_code
```

**Bước 2:** Cài đặt các thư viện cần thiết bằng tệp cấu hình:
```bash
pip install -r requirements.txt
```

**Bước 3:** Khởi động máy chủ ứng dụng:
```bash
python app.py
```

**Bước 4:** Mở trình duyệt và truy cập đường dẫn:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 📖 Luồng thao tác (Workflow)

1. **Sinh dữ liệu thử nghiệm:** Tại bảng điều khiển số 1, nhập số lượng phần tử cần test và bấm *Tạo & Tải Xuống*. (Hệ thống sẽ sinh một file `.bin` chứa các số thực Double 8-bytes ngẫu nhiên).
2. **Thiết lập phần cứng:** Tại bảng điều khiển số 2, tùy chỉnh sức chứa RAM và số luồng ghi File tạm.
3. **Sắp xếp:** Tải lên file `.bin` vừa tạo và bấm *Bắt đầu Sắp xếp Ngoại*.
4. **Quan sát:** - Sử dụng nút **Tiếp theo ▶** để xem quá trình thuật toán xử lý dữ liệu.
   - Các file có số lượng lớn (lớn hơn 40 phần tử) sẽ được in kết quả xử lý qua bảng Log hệ thống thay vì vẽ đồ họa.
5. **Kiểm chứng:** Sử dụng các nút *Xem Dữ Liệu Gốc* và *Xem Dữ Liệu Sắp Xếp* để đọc trực tiếp kết quả nhị phân ra màn hình.
