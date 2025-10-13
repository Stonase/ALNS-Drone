import copy, random, numpy as np
from collections import defaultdict

def random_remove(data, solution, q=5):
    destroyed = copy.deepcopy(solution)
    removed = []
    for _ in range(q):
        route_idx = random.choice([i for i, r in enumerate(destroyed) if len(r) > 2])
        node_idx = random.randint(1, len(destroyed[route_idx]) - 2)
        removed.append(destroyed[route_idx].pop(node_idx))
    return destroyed, removed

def worst_energy_remove(data, solution, q=5):
    """修复版高能耗节点移除：避免索引越界"""
    energy_cost = {}
    
    # 1. 收集所有有效位置的能耗差
    for route_idx, route in enumerate(solution):
        if len(route) <= 2:  # 跳过空路径和无效路径
            continue
        for pos in range(1, len(route)-1):  # 仅处理中间节点
            prev, curr, next_ = route[pos-1], route[pos], route[pos+1]
            original = data.dist_matrix[prev][curr] + data.dist_matrix[curr][next_]
            detour = data.dist_matrix[prev][next_]
            energy_cost[(route_idx, pos)] = original - detour  # 存储差值
    
    # 2. 按能耗差降序排序，并分组处理
    sorted_items = sorted(energy_cost.items(), key=lambda x: -x[1])[:q]
    
    # 3. 按路径分组并从后往前移除
    removal_plan = defaultdict(list)
    for (route_idx, pos), _ in sorted_items:
        removal_plan[route_idx].append(pos)
    
    destroyed = copy.deepcopy(solution)
    removed = []
    
    # 4. 执行实际移除操作
    for route_idx in removal_plan:
        # 必须按逆序移除，避免索引失效
        for pos in sorted(removal_plan[route_idx], reverse=True):
            # 二次验证路径长度
            if 1 <= pos < len(destroyed[route_idx])-1:
                removed.append(destroyed[route_idx].pop(pos))
    
    # 5. 路径格式强制修正
    for route in destroyed:
        if len(route) < 2 or route[0] != data.depot_id or route[-1] != data.depot_id:
            route[:] = [data.depot_id, data.depot_id]
    
    return destroyed, removed[:q]  # 返回至多q个移除节点

DESTROY_OPERATORS = [random_remove, worst_energy_remove]

