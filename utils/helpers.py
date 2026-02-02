import copy

def route_feasibility_check(data, cfg, route):
    """路径可行性验证"""
    # 1. 检查路径首尾是否为车场
    if route[0] != data.depot_id or route[-1] != data.depot_id:
        return (False, None)
    
    # 2. 检查车辆容量
    total_demand = sum(data.demands[node] for node in route if node in data.customer_ids)
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

def handle_unassigned_customers(data, cfg, solution):
    """
    #1122 目前新车安排的逻辑还是比较牵强。
    处理未分配客户：检查并尝试用新车安排未分配客户
    参数：
        data: 数据对象
        cfg: 配置对象
        solution: 当前解决方案（路径列表）
    返回：
        processed_solution: 处理后的解决方案
        has_unassigned: 是否仍有未分配客户（布尔值）
    """
    # 步骤1：检查未分配客户
    assigned = set()
    for route in solution:
        assigned.update(node for node in route if node in data.customer_ids)
    unassigned = list(set(data.customer_ids) - assigned)
    if not unassigned:
        return solution, False  # 无未分配客户，直接返回

    # 步骤2：统计当前已用车辆数（非空车）
    used_vehicles = sum(1 for route in solution if len(route) > 2)
    max_vehicles = cfg.vehicle_num

    # 步骤3：若有剩余车辆额度，尝试用新车安排
    if used_vehicles < max_vehicles:
        # 为未分配客户创建初始路径（车场->客户->车场）
        new_route = [data.depot_id] + unassigned + [data.depot_id]
        feasible, _ = route_feasibility_check(data, cfg, new_route)

        # 若路径不可行，按最近邻拆分客户
        if not feasible:
            from ..initial_solution import nearest_neighbor_sort
            sorted_unassigned = nearest_neighbor_sort(data, unassigned, data.depot_id)
            # 逐步减少客户数量直到路径可行
            for k in range(len(sorted_unassigned), 0, -1):
                partial_route = [data.depot_id] + sorted_unassigned[:k] + [data.depot_id]
                if route_feasibility_check(data, cfg, partial_route)[0]:
                    new_route = partial_route
                    unassigned = sorted_unassigned[k:]  # 更新剩余未分配客户
                    break
            else:
                # 即使单客户也不可行（极端情况），返回原解决方案
                return solution, True

        # 将新车路径插入解决方案（替换第一个空车位置）
        processed_solution = copy.deepcopy(solution)
        empty_veh_idx = next(i for i, r in enumerate(processed_solution) if len(r) <= 2)
        processed_solution[empty_veh_idx] = new_route

        # 递归处理剩余未分配客户（若仍有剩余且车辆充足）
        if unassigned and (used_vehicles + 1) < max_vehicles:
            return handle_unassigned_customers(data, cfg, processed_solution)
        return processed_solution, bool(unassigned)

    # 步骤4：无剩余车辆，返回原解决方案
    return solution, True

def check_unassigned_customers(data, solution):
    """检查是否有未分配的客户"""
    assigned = set()
    for route in solution:
        assigned.update(node for node in route if node in data.customer_ids)
    unassigned = set(data.customer_ids) - assigned
    return list(unassigned)

def rearrange_empty_vehicles(solution):
    """将空车（仅含首尾车场的路径）移到解的末尾"""
    non_empty = [route for route in solution if len(route) > 2]  # 非空车辆
    empty = [route for route in solution if len(route) <= 2]      # 空车
    return non_empty + empty  # 非空车在前，空车在后

import copy

def adjust_charge_stations(data, cfg, route):
    """
    调整路径中现有换电站的位置至最优
    修改版：
    1. 引入成本导向：优先考虑行驶距离成本。
    2. 安全底线：对剩余电量低于安全阈值（10%）的方案施加重罚。
    3. 保留用户逻辑：使用 (0.7*pre + 0.3*post) 作为优选奖励，倾向于前向冗余。
    """
    # 1. 提取路径中现有换电站及其位置
    existing_charges = [(i, node) for i, node in enumerate(route) if node in data.charge_ids]
    
    # 若无充电站，回退到插入逻辑
    if not existing_charges:
        return charging_insert(data, cfg, route)

    original_route = copy.deepcopy(route)
    best_route = None
    min_score = float('inf')  # 评分越低越好
    
    # 2. 遍历每一个现有的充电站，尝试将其移动到更优位置
    for charge_pos, charge_node in existing_charges:
        # A. 临时移除当前充电站
        temp_route = original_route[:charge_pos] + original_route[charge_pos+1:]
        
        # B. 遍历所有可能的插入位置
        for new_pos in range(1, len(temp_route) - 1):
            # 避免在其他充电站紧后插入
            if temp_route[new_pos] in data.charge_ids:
                continue
            
            # 构造候选路径
            candidate_route = temp_route[:new_pos+1] + [charge_node] + temp_route[new_pos+1:]
            
            # C. 可行性检查
            is_feasible, _ = route_feasibility_check(data, cfg, candidate_route)
            if not is_feasible:
                continue
            
            # D. 计算核心指标
            
            # 1. 运营成本 (Cost)：解决绕路问题的关键
            # 直接计算新路径的成本（距离费+充电费等）
            cost = solution_cost(data, cfg, [candidate_route])
            
            # 2. 冗余度计算
            # calculate_redundancy 内部已减去 10% 的安全阈值
            pre_redundancy, post_redundancy = calculate_redundancy(data, cfg, candidate_route, new_pos+1)
            
            # 3. 安全短板 (Safety Floor)
            min_redundancy = min(pre_redundancy, post_redundancy)
            
            # 4. 加权冗余度 (User's Formula) - 用作奖励
            # 保留您要求的逻辑：更看重到达充电站前的冗余
            weighted_redundancy = 0.7 * pre_redundancy + 0.3 * post_redundancy
            
            # E. 综合评分 (Score Calculation)
            penalty = 0
            
            # 惩罚机制：如果任何一段的电量跌破安全线(10%)，施加惩罚
            # 这能解决“结束电量比: 0.01”的危险情况
            if min_redundancy <= 0:
                penalty = 10000.0
            
            # 评分公式：Score = 成本 + 惩罚 - (冗余奖励 * 权重)
            # 权重设为 10.0，意味着 0.1 的冗余度优势可以抵消约 1.0 元的距离成本
            # 这样既不会为了微小的电量优势绕远路，也能在同等距离下选电量更好的
            score = cost + penalty - (weighted_redundancy * 10.0)
            
            if score < min_score:
                min_score = score
                best_route = candidate_route

    # 3. 返回最优结果
    if best_route is not None:
        return (True, best_route)
    
    # 4. 调整失败，尝试插入新站点
    return charging_insert(data, cfg, original_route)

# def adjust_charge_stations(data, cfg, route):
#     """
#     调整路径中现有换电站的位置至最优（优先调整，其次添加）
#     核心目标：换电站前后均保持电量冗余，适应负载变化导致的能耗差异
#     返回：(是否成功, 调整后的路径)
#     """
#     # 1. 提取路径中现有换电站及其位置
#     existing_charges = [(i, node) for i, node in enumerate(route) if node in data.charge_ids]
#     original_route = copy.deepcopy(route)
#     best_route = None
#     max_redundancy = -float('inf')  # 冗余度评分（越高越好）

#     # 2. 尝试调整现有换电站位置
#     if existing_charges:
#         for charge_pos, charge_node in existing_charges:
#             # 移除当前换电站，准备重新插入
#             temp_route = original_route[:charge_pos] + original_route[charge_pos+1:]
            
#             # 遍历所有可能的插入位置（排除首尾车场）
#             for new_pos in range(1, len(temp_route)-1):
#                 # 只在客户节点后插入（避免连续充电站）
#                 if temp_route[new_pos] not in data.customer_ids:
#                     continue
                
#                 # 插入换电站并验证可行性
#                 candidate_route = temp_route[:new_pos+1] + [charge_node] + temp_route[new_pos+1:]
#                 feasible, _ = route_feasibility_check(data, cfg, candidate_route)
#                 if not feasible:
#                     continue
                
#                 # 计算换电站前后的电量冗余度
#                 pre_redundancy, post_redundancy = calculate_redundancy(data, cfg, candidate_route, new_pos+1)
#                 # 综合冗余评分：更关注前向冗余（初始负载高，能耗快）
#                 total_redundancy = 0.7 * pre_redundancy + 0.3 * post_redundancy
                
#                 # 保留冗余度最高的路径
#                 if total_redundancy > max_redundancy:
#                     max_redundancy = total_redundancy
#                     best_route = candidate_route

#     # 3. 若调整现有换电站成功，返回最优路径
#     if best_route is not None:
#         return (True, best_route)
    
#     # 4. 调整失败，尝试添加新换电站（复用现有充电插入逻辑）
#     return charging_insert(data, cfg, original_route)


def calculate_redundancy(data, cfg, route, charge_pos):
    """
    计算换电站位置的电量冗余度：
    - 前向冗余：到达换电站时的剩余电量（相对于最低安全阈值）
    - 后向冗余：离开换电站后到终点的剩余电量（相对于最低安全阈值）
    """
    # 前向计算：从起点到换电站的电量变化
    current_energy = cfg.battery_cap
    current_load = sum(data.demands[node] for node in route if node in data.customer_ids)
    
    for i in range(1, charge_pos + 1):
        prev_node = route[i-1]
        curr_node = route[i]
        
        # 到达客户点时卸货（降低负载）
        if curr_node in data.customer_ids:
            current_load -= data.demands[curr_node]
        
        # 计算能耗
        distance = data.dist_matrix[prev_node][curr_node]
        energy_cost = distance * (cfg.base_energy + cfg.load_energy * current_load)
        current_energy -= energy_cost
        
        # 到达换电站时停止计算
        if i == charge_pos:
            break
    
    # 前向冗余：实际剩余电量 - 安全阈值（预留10%电量）
    pre_redundancy = current_energy - (cfg.battery_cap * 0.1)

    # 后向计算：从换电站到终点的电量变化（从满电开始）
    current_energy = cfg.battery_cap  # 换电站后电量重置为满电
    for i in range(charge_pos + 1, len(route)):
        prev_node = route[i-1]
        curr_node = route[i]
        
        if curr_node in data.customer_ids:
            current_load -= data.demands[curr_node]
        
        distance = data.dist_matrix[prev_node][curr_node]
        energy_cost = distance * (cfg.base_energy + cfg.load_energy * current_load)
        current_energy -= energy_cost
    
    # 后向冗余：实际剩余电量 - 安全阈值
    post_redundancy = current_energy - (cfg.battery_cap * 0.1)
    
    return (max(pre_redundancy, 0), max(post_redundancy, 0))  # 负冗余按0计算