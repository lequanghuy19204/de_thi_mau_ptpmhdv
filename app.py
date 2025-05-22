from flask import Flask, request, jsonify, render_template
import sqlite3
import os

app = Flask(__name__)

# Đường dẫn đến file database
DB_PATH = 'order.db'

# Kiểm tra xem database đã tồn tại chưa
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ma_hang TEXT NOT NULL,
    ten_hang TEXT NOT NULL,
    so_luong INTEGER NOT NULL,
    don_gia REAL NOT NULL,
    thanh_tien REAL NOT NULL
)
''')
conn.commit()
conn.close()

# Hàm kết nối database
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# API endpoint để lấy tất cả đơn hàng
@app.route('/api/orders', methods=['GET'])
def get_orders():
    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM orders').fetchall()
    conn.close()
    
    result = []
    for order in orders:
        result.append({
            'id': order['id'],
            'ma_hang': order['ma_hang'],
            'ten_hang': order['ten_hang'],
            'so_luong': order['so_luong'],
            'don_gia': order['don_gia'],
            'thanh_tien': order['thanh_tien']
        })
    
    return jsonify(result)

# API endpoint để lấy một đơn hàng theo ID
@app.route('/api/orders/<int:id>', methods=['GET'])
def get_order(id):
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if order is None:
        return jsonify({'error': 'Không tìm thấy đơn hàng'}), 404
    
    return jsonify({
        'id': order['id'],
        'ma_hang': order['ma_hang'],
        'ten_hang': order['ten_hang'],
        'so_luong': order['so_luong'],
        'don_gia': order['don_gia'],
        'thanh_tien': order['thanh_tien']
    })

# API endpoint để thêm đơn hàng mới
@app.route('/api/orders', methods=['POST'])
def add_order():
    if not request.json:
        return jsonify({'error': 'Dữ liệu không hợp lệ'}), 400
    
    data = request.json
    required_fields = ['ma_hang', 'ten_hang', 'so_luong', 'don_gia']
    
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Thiếu trường {field}'}), 400
    
    # Sử dụng dịch vụ tính thành tiền
    so_luong = data['so_luong']
    don_gia = data['don_gia']
    # Gọi hàm tính thành tiền
    thanh_tien = calculate_total_amount(so_luong, don_gia)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO orders (ma_hang, ten_hang, so_luong, don_gia, thanh_tien) VALUES (?, ?, ?, ?, ?)',
        (data['ma_hang'], data['ten_hang'], so_luong, don_gia, thanh_tien)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    return jsonify({
        'id': new_id,
        'ma_hang': data['ma_hang'],
        'ten_hang': data['ten_hang'],
        'so_luong': so_luong,
        'don_gia': don_gia,
        'thanh_tien': thanh_tien
    }), 201

# API endpoint để cập nhật đơn hàng
@app.route('/api/orders/<int:id>', methods=['PUT'])
def update_order(id):
    if not request.json:
        return jsonify({'error': 'Dữ liệu không hợp lệ'}), 400
    
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (id,)).fetchone()
    
    if order is None:
        conn.close()
        return jsonify({'error': 'Không tìm thấy đơn hàng'}), 404
    
    data = request.json
    ma_hang = data.get('ma_hang', order['ma_hang'])
    ten_hang = data.get('ten_hang', order['ten_hang'])
    so_luong = data.get('so_luong', order['so_luong'])
    don_gia = data.get('don_gia', order['don_gia'])
    
    # Sử dụng dịch vụ tính thành tiền
    thanh_tien = calculate_total_amount(so_luong, don_gia)
    
    conn.execute(
        'UPDATE orders SET ma_hang = ?, ten_hang = ?, so_luong = ?, don_gia = ?, thanh_tien = ? WHERE id = ?',
        (ma_hang, ten_hang, so_luong, don_gia, thanh_tien, id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        'id': id,
        'ma_hang': ma_hang,
        'ten_hang': ten_hang,
        'so_luong': so_luong,
        'don_gia': don_gia,
        'thanh_tien': thanh_tien
    })

# API endpoint để xóa đơn hàng
@app.route('/api/orders/<int:id>', methods=['DELETE'])
def delete_order(id):
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (id,)).fetchone()
    
    if order is None:
        conn.close()
        return jsonify({'error': 'Không tìm thấy đơn hàng'}), 404
    
    conn.execute('DELETE FROM orders WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': f'Đơn hàng với ID {id} đã được xóa'})

# API endpoint để tính thành tiền
@app.route('/api/calculate-total', methods=['POST'])
def calculate_total():
    if not request.json:
        return jsonify({'error': 'Dữ liệu không hợp lệ'}), 400
    
    data = request.json
    required_fields = ['so_luong', 'don_gia']
    
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Thiếu trường {field}'}), 400
    
    # Tính thành tiền
    so_luong = data['so_luong']
    don_gia = data['don_gia']
    thanh_tien = so_luong * don_gia
    
    return jsonify({
        'so_luong': so_luong,
        'don_gia': don_gia,
        'thanh_tien': thanh_tien
    })

# API endpoint để tính tổng thành tiền các đơn hàng
@app.route('/api/calculate-total-sum', methods=['GET'])
def calculate_total_sum():
    conn = get_db_connection()
    result = conn.execute('SELECT SUM(thanh_tien) as tong_tien FROM orders').fetchone()
    conn.close()
    
    tong_tien = result['tong_tien'] if result['tong_tien'] is not None else 0
    
    return jsonify({
        'tong_tien': tong_tien
    })

# Hàm tính thành tiền (dịch vụ)
def calculate_total_amount(so_luong, don_gia):
    return so_luong * don_gia

# Thêm route cho trang chủ
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
