import numpy as np
import pandas as pd

class VRPData:
    """问题数据容器"""
    def __init__(self):
        self.node_df = None       # 原始数据DataFrame
        self.depot_id = 0         # 车场节点ID
        self.customer_ids = []    # 客户点ID列表
        self.charge_ids = []      # 充电站ID列表 
        self.dist_matrix = []     # 距离矩阵(numpy)
        self.demands = []         # 节点需求列表
        self.coords = []          # 节点坐标列表

        self.nearest_charge = {}  # 最近充电站