def route_feasibility_check(data, cfg, route):
    """路径可行性验证"""
    # 1. 检查路径首尾是否为车场
    if route[0] != data.depot_id or route[-1] != data.depot_id:
        return (False, None)
    
    # 2. 检查车辆容量
    total_demand = sum(
        data.demands[node]
        for node in route
        if node in data.customer_ids
    )
    if total_demand > cfg.car_capacity:
        return (False, None)
    
    # 3. 初始化负载与能量
    current_load = total_demand
    current_energy = cfg.battery_cap
    min_energy = float('inf')
    
    for i in range(1, len(route)):
        prev_node = route[i-1]
        curr_node = route[i]
        
        # 到达客户点时卸货
        if curr_node in data.customer_ids:
            current_load -= data.demands[curr_node]
        
        # 计算能耗
        distance = data.dist_matrix[prev_node][curr_node]
        energy_cost = distance * (cfg.base_energy + cfg.load_energy * current_load)
        current_energy -= energy_cost
        min_energy = min(min_energy, current_energy)
        
        # 充电站充电
        if curr_node in data.charge_ids:
            current_energy = cfg.battery_cap
    
    return (min_energy >= 0, current_energy / cfg.battery_cap)

def charging_insert(data, cfg, route):
    """最近换电站插入修复"""
    # 1. 将route中逐个客户尝试在该客户后插入其最近的充电站
    # 2. 可行性测试，返回剩余电量
    # 3. 选择可行且剩余电量最多的换电插入方式，插入一个充电站，返回true和插入后的路径
    # 4. 不可行则返回false和原来路径
    # 基本验证：路径应以车场(depot)起止
    best_route = None
    best_remaining = -1.0

    # 遍历路径中每个客户节点（排除出发点和终点）
    for i in range(1, len(route) - 1):
        node = route[i]
        # 只在客户节点后尝试插入充电站
        if node not in data.customer_ids:
            continue

        # 找到该客户最近的充电站（按静态距离矩阵）
        nearest_charge = data.nearest_charge.get(node, None)

        if nearest_charge is None:
            continue

        # 如果下一个节点已经是该充电站，则跳过（无需重复插入）
        if i + 1 < len(route) and route[i + 1] == nearest_charge:
            continue

        # 试探性插入：在 node 之后插入 nearest_charge
        new_route = route[:i+1] + [nearest_charge] + route[i+1:]

        feasible, remaining = route_feasibility_check(data, cfg, new_route)
        # remaining 为结束时的剩余能量比（0..1），feasible 为布尔
        if feasible:
            # 选择剩余能量最大的可行方案
            if remaining > best_remaining:
                best_remaining = remaining
                best_route = new_route

    if best_route is not None:
        return (True, best_route)

    return (False, route)

def solution_cost(data, cfg, solution):
    #车辆使用成本
    used_vehicles = sum(1 for r in solution if len(r) > 2)
    total_cost = used_vehicles * cfg.vehicle_fixed_cost
    #行驶距离成本
    total_distance = sum(data.dist_matrix[r[i-1]][r[i]] for r in solution for i in range(1, len(r)))
    total_cost += total_distance * cfg.distance_cost
    #车辆充电成本
    charging_count = sum(1 for route in solution for node in route if node in data.charge_ids)
    total_cost += charging_count * cfg.charging_cost
    return total_cost
