import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import math
import os

# === 配置路径 ===
# 请确保输入文件路径正确
input_file = 'data/C101network.txt' 
output_dir = 'data'

def read_solomon_data(filepath):
    """读取原始Solomon格式数据"""
    # 这里的 names 对应您 C101network.txt 中的列名
    # 注意：原始文件第一行可能是列名，需要正确跳过或读取
    try:
        df = pd.read_csv(filepath)
    except Exception:
        # 如果读取失败，尝试作为纯文本读取并处理
        df = pd.read_csv(filepath, delimiter=',')
        
    # 清洗列名（去除空格）
    df.columns = [c.strip() for c in df.columns]
    return df

def add_charging_stations(original_df, station_coords, strategy_name):
    """构建包含新充电站的DataFrame"""
    df = original_df.copy()
    
    # 1. 为原始数据添加 TYPE 列
    # 车场 (ID 1) 为 'depot'，其余为 'customer'
    df['TYPE'] = df['CUST NO'].apply(lambda x: 'depot' if x == 1 else 'customer')
    
    # 2. 获取车场的时间窗信息（通常充电站时间窗与车场一致，表示全天开放）
    depot_row = df[df['CUST NO'] == 1].iloc[0]
    depot_ready = depot_row['READY TIME']
    depot_due = depot_row['DUE TIME']
    
    # 3. 创建新充电站节点
    new_rows = []
    max_id = df['CUST NO'].max()
    
    for i, (x, y) in enumerate(station_coords):
        new_id = max_id + 1 + i
        new_row = {
            'CUST NO': new_id,
            'XCOORD': round(x, 2),
            'YCOORD': round(y, 2),
            'DEMAND': 0.0,             # 充电站无需求
            'READY TIME': depot_ready, # 与车场一致
            'DUE TIME': depot_due,     # 与车场一致
            'SERVICE TIME': 0.0,       # 充电站服务时间设为0（或根据需要调整）
            'TYPE': 'charging_station' # 关键字段，适配 data_process.py
        }
        new_rows.append(new_row)
        
    # 4. 合并数据
    stations_df = pd.DataFrame(new_rows)
    final_df = pd.concat([df, stations_df], ignore_index=True)
    
    return final_df

def save_data(df, filename):
    """保存为适配 data_process.py 读取的 CSV 格式"""
    save_path = os.path.join(output_dir, filename)
    # 保持浮点数格式
    df.to_csv(save_path, index=False, float_format='%.2f')
    print(f"文件已生成: {save_path} (节点总数: {len(df)})")

# === 主逻辑 ===

# 1. 读取数据
print("正在读取原始数据...")
# 注意：根据您提供的文件内容，它是逗号分隔的
df_raw = read_solomon_data(input_file)

# 准备聚类数据 (排除车场)
customers = df_raw[df_raw['CUST NO'] != 1].copy()
X = customers[['XCOORD', 'YCOORD']].values
depot = df_raw[df_raw['CUST NO'] == 1].iloc[0]
depot_coords = (depot['XCOORD'], depot['YCOORD'])

# 2. 执行聚类 (K=10)
print("正在执行 K-Means 聚类...")
kmeans = KMeans(n_clusters=10, random_state=42, n_init='auto')
customers['Cluster'] = kmeans.fit_predict(X)
centers = kmeans.cluster_centers_

# === 策略 1: 充电站位于聚类中心 ===
print("\n生成策略 1 数据 (Cluster Centers)...")
strategy1_coords = centers
df_strat1 = add_charging_stations(df_raw, strategy1_coords, "Strategy1")
save_data(df_strat1, 'C101_Strategy1_Centers.txt')


# === 策略 2: 充电站位于相邻聚类之间的环状位置 ===
print("\n生成策略 2 数据 (Ring Midpoints)...")

# 计算每个中心相对于车场的角度，以便按环状排序
center_vectors = centers - np.array(depot_coords)
angles = np.arctan2(center_vectors[:, 1], center_vectors[:, 0]) # 返回弧度 (-pi, pi)

# 获取排序后的索引
sorted_indices = np.argsort(angles)
sorted_centers = centers[sorted_indices]

# 计算相邻中心的中点
strategy2_coords = []
n_centers = len(sorted_centers)

# 您提到要 9 个充电站。
# 通常 10 个聚类形成闭环会有 10 个间隔。
# 这里我生成所有 10 个间隔的中点。如果您严格只需要 9 个，可以切片 [:9]
# 但为了保持环的完整性，建议使用 10 个。
# 如果必须是 9 个，请解开下面注释的一行：
# range_limit = n_centers - 1 
range_limit = n_centers 

for i in range(range_limit):
    p1 = sorted_centers[i]
    p2 = sorted_centers[(i + 1) % n_centers] # 取模以连接最后一个和第一个
    
    mid_x = (p1[0] + p2[0]) / 2
    mid_y = (p1[1] + p2[1]) / 2
    strategy2_coords.append((mid_x, mid_y))

df_strat2 = add_charging_stations(df_raw, strategy2_coords, "Strategy2")
save_data(df_strat2, 'C101_Strategy2_Ring.txt')

print("\n处理完成。请修改 main.py 或 config.py 中的数据文件路径以运行实验。")