def route_feasibility_check(data, cfg, route):
    """路径可行性验证"""
    # 1. 检查路径首尾是否为车场
    if route[0] != data.depot_id or route[-1] != data.depot_id:
        return (False, 0)
    
    # 2. 检查车辆容量
    total_demand = sum(
        data.demands[node]
        for node in route
        if node in data.customer_ids
    )
    if total_demand > cfg.car_capacity:
        return (False, 0)
    
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
        energy_cost = distance * energy_consumption(cfg, current_load)
        current_energy -= energy_cost
        min_energy = min(min_energy, current_energy)
        
        # 充电站充电
        if curr_node in data.charge_ids:
            current_energy = cfg.battery_cap
    
    return (min_energy >= 0, min_energy)


def energy_consumption(cfg, load):
    """单位距离能耗：α + β*load"""
    return cfg.base_energy + cfg.load_energy * load


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
