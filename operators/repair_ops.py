from copy import deepcopy
from ..utils.helpers import route_feasibility_check, solution_cost, adjust_charge_stations

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
        # 若无法插入则需考虑该客户如何安放，但是目前暂未考虑
    return destroyed

def vehicle_reinsert(data, cfg, destroyed, removed):
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

def nearest_adjust_insert(data, cfg, destroyed, removed):
    """
    基于最近邻的自适应修复算子：
    1. 优先插入到最近客户所在车辆
    2. 不可行时调整换电站位置（支持1-2个充电站）
    3. 仍不可行时移除距离差最大的客户并重新分配
    """
    # 待插入客户队列（可能因重分配增加）
    to_insert = deepcopy(removed)
    
    while to_insert:
        customer = to_insert.pop(0)
        # 步骤1：找到该客户最近的已分配客户及其所在车辆
        nearest_cust, min_dist = None, float('inf')
        target_route_idx, target_pos = None, None
        
        # 遍历所有非空车辆，寻找最近的已分配客户
        for route_idx, route in enumerate(destroyed):
            if len(route) <= 2:
                continue  # 跳过空车
            # 检查路径中的客户节点（排除车场和充电站）
            for pos, node in enumerate(route[1:-1]):
                if node in data.customer_ids:  # 仅考虑客户节点
                    dist = data.dist_matrix[customer][node]
                    if dist < min_dist:
                        min_dist = dist
                        nearest_cust = node
                        target_route_idx = route_idx
                        target_pos = pos + 1  # 插入到该客户后面
        
        # 若未找到目标车辆（所有车为空），直接用空车创建路径
        if target_route_idx is None:
            empty_route_idx = next(i for i, r in enumerate(destroyed) if len(r) <= 2)
            new_route = [data.depot_id, customer, data.depot_id]
            destroyed[empty_route_idx] = new_route
            continue
        
        # 步骤2：尝试在目标位置插入客户
        target_route = deepcopy(destroyed[target_route_idx])
        # 插入到最近客户后面（pos为目标位置）
        inserted_route = target_route[:target_pos+1] + [customer] + target_route[target_pos+1:]
        feasible, _ = route_feasibility_check(data, cfg, inserted_route)
        
        if feasible:
            destroyed[target_route_idx] = inserted_route
            continue
        
        # 步骤3：不可行时调整换电站（先尝试单站调整，再尝试双站）
        adjusted_route = None
        success, adjusted_route = adjust_charge_stations(data, cfg, inserted_route)

        # 若调整换电站后可行，更新路径
        if adjusted_route and route_feasibility_check(data, cfg, adjusted_route)[0]:
            destroyed[target_route_idx] = adjusted_route
            continue
        
        # 步骤4：仍不可行，移除路径中距离差最大的客户（优先移除能最大化缩短距离的客户）
        target_route = inserted_route  # 基于插入后的路径计算
        max_diff = -float('inf')
        remove_pos = -1
        remove_cust = None
        
        # 计算每个客户的移除距离差（移除后节省的距离）
        for pos in range(1, len(target_route) - 1):
            node = target_route[pos]
            if node not in data.customer_ids:
                continue  # 不移除充电站
            prev = target_route[pos-1]
            next_node = target_route[pos+1]
            # 原始距离：prev->node->next；移除后：prev->next
            diff = (data.dist_matrix[prev][node] + data.dist_matrix[node][next_node]) - data.dist_matrix[prev][next_node]
            if diff > max_diff:
                max_diff = diff
                remove_pos = pos
                remove_cust = node
        
        if remove_cust is not None:
            # 移除该客户，重新加入待插入队列
            new_route = target_route[:remove_pos] + target_route[remove_pos+1:]
            # 验证移除后的路径可行性
            if route_feasibility_check(data, cfg, new_route)[0]:
                destroyed[target_route_idx] = new_route
                to_insert.append(remove_cust)  # 重新分配被移除的客户
                to_insert.append(customer)     # 重新尝试插入当前客户
                continue
        
        # 极端情况：上述方法均失败，使用空车单独分配
        empty_route_idx = next((i for i, r in enumerate(destroyed) if len(r) <= 2), None)
        if empty_route_idx is not None:
            destroyed[empty_route_idx] = [data.depot_id, customer, data.depot_id]
    
    return destroyed

REPAIR_OPERATORS = [greedy_insert,nearest_adjust_insert]
