import copy
from .utils.helpers import route_feasibility_check,solution_cost

def generate_initial_solution(data, cfg):
    depot = data.depot_id
    routes = [[depot, depot] for _ in range(cfg.vehicle_num)]
    remaining = data.customer_ids.copy()
    used_vehicle_count = 1

    while remaining:
        sorted_customers = nearest_neighbor_sort(data, remaining, depot)
        for cust in sorted_customers.copy():
            best_cost, best_route, best_pos = float('inf'), None, None
            # 遍历所有已用车辆，寻找最优插入位置
            for route_idx in range(used_vehicle_count):
                route = routes[route_idx]
                for pos in range(1, len(route)):
                    new_route = route[:pos] + [cust] + route[pos:]
                    feasible, _ = route_feasibility_check(data, cfg, new_route)
                    if feasible:
                        cost = solution_cost(data, cfg, [new_route])
                        if cost < best_cost:
                            best_cost, best_route, best_pos = cost, route_idx, pos
            if best_route is not None:
                routes[best_route].insert(best_pos, cust)
                remaining.remove(cust)
            elif used_vehicle_count < cfg.vehicle_num:
                used_vehicle_count += 1
                break
            else:
                raise ValueError(f"客户 {cust} 无法分配")
    return routes

def nearest_neighbor_sort(data, remaining_customers, depot):
    sorted_customers = []
    current = depot
    unvisited = set(remaining_customers)
    while unvisited:
        nearest, min_dist = None, float('inf')
        for node in unvisited:
            d = data.dist_matrix[current][node]
            if d < min_dist:
                min_dist, nearest = d, node
        sorted_customers.append(nearest)
        unvisited.remove(nearest)
        current = nearest
    return sorted_customers
