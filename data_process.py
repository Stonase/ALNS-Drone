import numpy as np
import pandas as pd
from .data_structure import VRPData
from pathlib import Path

def load_data(file_path: str) -> VRPData:
    """
    读取并预处理输入数据
    参数：
        file_path: 数据文件路径
    返回：
        VRPData: 结构化数据对象
    """
    data = VRPData()
    base_dir = Path(__file__).resolve().parent
    data_path = base_dir / "data" / "C101_Strategy1_Centers.txt"
    # 原始数据读取
    raw_df = pd.read_csv(data_path)
    data.node_df = raw_df
    
    # 节点分类处理
    depot = raw_df[raw_df['CUST NO'] == 1].iloc[0]
    data.depot_id = 0
    data.coords = [(depot['XCOORD'], depot['YCOORD'])]  # 车场坐标
    
    for _, row in raw_df.iterrows():
        if row['CUST NO'] == 1:
            continue  # 跳过车场重复处理
        
        node_type = str(row['TYPE']).lower().strip()
        data.coords.append((row['XCOORD'], row['YCOORD']))
        
        if node_type == 'charging_station':
            data.charge_ids.append(row['CUST NO'] - 1)
        else:
            data.customer_ids.append(int(row['CUST NO'] - 1))
    
    # 构建距离矩阵
    n = len(data.coords)
    data.dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            data.dist_matrix[i][j] = np.hypot(
                data.coords[i][0]-data.coords[j][0],
                data.coords[i][1]-data.coords[j][1]
            )
    
    # 为每个客户计算最近充电站
    for cust in data.customer_ids:
        min_dist = float('inf')
        nearest_station = None
        
        for chg in data.charge_ids:
            d = data.dist_matrix[cust][chg]
            if d < min_dist:
                min_dist = d
                nearest_station = chg
        
        if nearest_station is None:
            data.nearest_charge[cust] = None
        else:
            data.nearest_charge[cust] = nearest_station

    # 需求数据映射
    data.demands = [0] + [row['DEMAND'] for _, row in raw_df.iterrows() if row['CUST NO'] != 1]
    
    return data