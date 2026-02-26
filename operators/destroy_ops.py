import copy, random, numpy as np
from collections import defaultdict

def random_remove(data, cfg, solution, q=20):
    destroyed = copy.deepcopy(solution)
    removed = []
    
    # 1. 收集所有合法的【客户节点】位置
    removable_pool = []
    for r_idx, route in enumerate(destroyed):
        for pos in range(1, len(route) - 1):
            # 核心修复：如果该节点不是客户（即为换电站），绝对不允许移除！
            if route[pos] in data.customer_ids:
                removable_pool.append((r_idx, pos))
    
    # 2. 确定要移除的数量，并随机选择
    actual_q = min(q, len(removable_pool))
    if actual_q == 0:
        return destroyed, removed
    to_remove = random.sample(removable_pool, actual_q)
    
    # 3. 按路径分组，并降序排序位置（从后往前pop，防止索引错位）
    removal_plan = defaultdict(list)
    for r_idx, pos in to_remove:
        removal_plan[r_idx].append(pos)
        
    for r_idx in removal_plan:
        for pos in sorted(removal_plan[r_idx], reverse=True):
            removed.append(destroyed[r_idx].pop(pos))
            
    return destroyed, removed

def worst_energy_remove(data, cfg, solution, q=20):
    """高能耗节点移除：避免索引越界"""
    energy_cost = {}
    
    # 1. 评估移除每个【客户节点】能节省的能耗（距离）
    for route_idx, route in enumerate(solution):
        if len(route) <= 2: 
            continue
        for pos in range(1, len(route)-1):  
            # 核心修复：跳过换电站，只评估移除客户的能耗差
            if route[pos] not in data.customer_ids:
                continue
                
            prev, curr, next_ = route[pos-1], route[pos], route[pos+1]
            original = data.dist_matrix[prev][curr] + data.dist_matrix[curr][next_]
            detour = data.dist_matrix[prev][next_]
            energy_cost[(route_idx, pos)] = original - detour 
    
    # 2. 按能耗差降序排序
    sorted_items = sorted(energy_cost.items(), key=lambda x: -x[1])[:q]
    
    removal_plan = defaultdict(list)
    for (route_idx, pos), _ in sorted_items:
        removal_plan[route_idx].append(pos)
    
    destroyed = copy.deepcopy(solution)
    removed = []
    
    # 3. 执行实际移除操作
    for route_idx in removal_plan:
        for pos in sorted(removal_plan[route_idx], reverse=True):
            removed.append(destroyed[route_idx].pop(pos))
    
    # 4. 路径格式安全兜底
    for route in destroyed:
        if len(route) < 2 or route[0] != data.depot_id or route[-1] != data.depot_id:
            route[:] = [data.depot_id, data.depot_id]
    
    return destroyed, removed

def underutilized_vehicle_destroy(data, cfg, solution, q=2):
    """
    破坏算子：破坏利用率低的车辆路径。
    :param data: 问题数据
    :param solution: 当前解，一个路径列表
    :param q: 要破坏的车辆数量（可以是一个范围，如1到2）
    :return: (destroyed_solution, removed_customers)
    """
    destroyed_solution = copy.deepcopy(solution)
    removed_customers = []
    
    # 1. 识别低利用率车辆的索引
    underutilized_vehicle_indices = []
    for idx, route in enumerate(destroyed_solution):
        # 计算路径上的客户数量（排除起点、终点和换电站）
        customer_demands = sum(data.demands[node] for node in route if node in data.customer_ids)
        if customer_demands <= cfg.underutilized_threshold and len(route) > 2:
            underutilized_vehicle_indices.append(idx)
    
    # 2. 策略：如果没有低利用率车辆，该怎么办？
    # Fallback Strategy: 随机选择一辆车，释放其一半的客户（至少一个）
    if not underutilized_vehicle_indices:
        # 随机选择一辆非空车辆
        non_empty_routes = [idx for idx, r in enumerate(destroyed_solution) if len(r) > 2]
        if not non_empty_routes:
            # 极端情况：所有车都是空的，无法破坏，返回原解
            return destroyed_solution, removed_customers
            
        selected_vehicle_idx = random.choice(non_empty_routes)
        route_to_destroy = destroyed_solution[selected_vehicle_idx]
        
        # 提取路径上的所有客户
        customers_on_route = [node for node in route_to_destroy if node in data.customer_ids]
        if not customers_on_route:
            return destroyed_solution, removed_customers

        # 决定要释放的客户数量
        num_to_remove = max(1, len(customers_on_route) // 2)
        customers_to_remove = random.sample(customers_on_route, num_to_remove)
        
        # 从路径中移除这些客户
        new_route = [node for node in route_to_destroy if node not in customers_to_remove]
        destroyed_solution[selected_vehicle_idx] = new_route
        removed_customers.extend(customers_to_remove)
        
        return destroyed_solution, removed_customers

    # 3. 如果有低利用率车辆
    # 随机选择 q 辆（或全部）低利用率车辆进行破坏
    num_vehicles_to_destroy = min(q, len(underutilized_vehicle_indices))
    selected_vehicle_indices = random.sample(underutilized_vehicle_indices, num_vehicles_to_destroy)
    
    for vehicle_idx in selected_vehicle_indices:
        route = destroyed_solution[vehicle_idx]
        # 提取路径上的所有客户
        customers_on_route = [node for node in route if node in data.customer_ids]
        if not customers_on_route:
            continue
            
        removed_customers.extend(customers_on_route)
        # 将该车辆路径重置为仅包含起点和终点（表示车辆空闲）
        destroyed_solution[vehicle_idx] = [data.depot_id, data.depot_id]

    return destroyed_solution, removed_customers

DESTROY_OPERATORS = [random_remove, worst_energy_remove, underutilized_vehicle_destroy]

