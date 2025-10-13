def route_feasibility_check(data, cfg, route):
    total_demand = sum(data.demands[node] for node in route if node in data.customer_ids)
    return (total_demand <= cfg.car_capacity, total_demand)

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
