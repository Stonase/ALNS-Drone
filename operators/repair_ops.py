from copy import deepcopy
from ..utils.helpers import route_feasibility_check, solution_cost

def greedy_insert(data, cfg, destroyed, removed):
    for customer in removed:
        best_cost = float('inf')
        best_route, best_pos = None, None
        for route_idx, route in enumerate(destroyed):
            for pos in range(1, len(route)):
                new_route = route[:pos] + [customer] + route[pos:]
                feasible, _ = route_feasibility_check(data, cfg, new_route)
                if feasible:
                    temp = deepcopy(destroyed)
                    temp[route_idx] = new_route
                    cost = solution_cost(data, cfg, temp)
                    if cost < best_cost:
                        best_cost, best_route, best_pos = cost, route_idx, pos
        if best_route is not None:
            destroyed[best_route].insert(best_pos, customer)
    return destroyed

def _vehicle_reinsert(data, cfg, destroyed, removed):
    """车辆级修复：将被移除节点重新分配到其他车辆"""
    # 阶段1：尝试插入现有车辆
    temp_solution = greedy_insert(data, cfg, destroyed, removed)
    
    # 阶段2：检查剩余未插入节点
    remaining = []
    for route in temp_solution:
        remaining.extend(route[1:-1])
    remaining = list(set(remaining))
    
    # 阶段3：启用空车辆插入剩余节点
    if remaining:
        empty_vehicles = [i for i, route in enumerate(temp_solution) if len(route) == 2]
        for veh_id in empty_vehicles:
            if not remaining:
                break
            # 构建新路径：车场 -> 节点 -> 车场
            new_route = [data.depot_id] + remaining[:] + [data.depot_id]
            if route_feasibility_check(data, cfg, new_route)[0]:
                temp_solution[veh_id] = new_route
                remaining = []
                break
            else:  # 逐步减少插入节点
                for k in range(len(remaining), 0, -1):
                    partial_route = [data.depot_id] + remaining[:k] + [data.depot_id]
                    if route_feasibility_check(data, cfg, partial_route)[0]:
                        temp_solution[veh_id] = partial_route
                        remaining = remaining[k:]
                        break
    return temp_solution

REPAIR_OPERATORS = [greedy_insert,_vehicle_reinsert]
