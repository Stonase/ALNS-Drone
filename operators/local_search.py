from ..utils.helpers import route_feasibility_check, solution_cost, adjust_charge_stations
from copy import deepcopy

def local_search_2opt(data, cfg, solution):
    """
    对每条路径进行 2-opt 优化。
    注意：无人机路径包含充电站，交换节点可能会导致电量不可行，
    所以每次 swap 后必须 check feasibility。
    """
    improved = True
    while improved:
        improved = False
        for r_idx, route in enumerate(solution):
            if len(route) < 4: continue # 节点太少不需要优化
            
            best_route = route
            # 遍历所有可能的切断点 i 和 j
            for i in range(1, len(route) - 2):
                for j in range(i + 1, len(route) - 1):
                    # 执行 2-opt 翻转： route[i:j+1] 翻转
                    new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]
                    
                    # 快速检查距离是否优化（这是 2-opt 的核心，先看距离）
                    # 仅比较变化的边的距离，避免全量计算
                    # dist(i-1, i) + dist(j, j+1)  VS  dist(i-1, j) + dist(i, j+1)
                    # 省略具体的距离计算代码... 假设 new_dist < old_dist
                    
                    # 关键：检查翻转后的电量可行性！ 
                    # 因为翻转可能导致某段路变长或充电站位置变动
                    is_feasible, _ = route_feasibility_check(data, cfg, new_route)
                    
                    if is_feasible:
                        # 计算实际成本（包含可能的等待时间等）
                        current_cost = solution_cost(data, cfg, [best_route])
                        new_cost = solution_cost(data, cfg, [new_route])
                        
                        if new_cost < current_cost:
                            solution[r_idx] = new_route
                            improved = True
                            # 贪婪策略：一找到改进就跳出，重新开始循环（或继续）
                            break 
                if improved: break
    return solution

def local_search_prune_stations(data, cfg, solution):
    """
    local_search_prune_stations 的 Docstring
    
    :param data: 说明
    :param cfg: 说明
    :param solution: 说明
    """
    for r_idx, route in enumerate(solution):
        # 找出所有充电站的位置
        station_indices = [i for i, node in enumerate(route) if node in data.charge_ids]
        
        # 尝试逐个移除
        for s_idx in reversed(station_indices): # 从后往前删，索引不乱
            new_route = route[:s_idx] + route[s_idx+1:]
            
            # 检查移除后是否依然可行
            is_feasible, _ = route_feasibility_check(data, cfg, new_route)
            if is_feasible:
                # 成功移除冗余站点！
                solution[r_idx] = new_route
                # 更新 route 以便继续尝试移除下一个
                route = new_route 
    return solution

    """
    跨路径 Relocate 局部搜索：
    尝试将客户节点从当前路径“拔出”，插入到其他路径（或本路径的其他位置）。
    如果目标路径由于电量不够而不可行，会自动尝试添加/调整换电站。
    """
    improved = True
    while improved:
        improved = False
        current_cost = solution_cost(data, cfg, solution)
        
        # 遍历所有可能被“拔出”节点的源车辆
        for r1_idx in range(len(solution)):
            route1 = solution[r1_idx]
            if len(route1) <= 2: 
                continue # 空车跳过
            
            # 遍历源车辆中的每一个节点
            for i in range(1, len(route1) - 1):
                node = route1[i]
                # 绝对保护：只允许搬移客户，不允许直接搬移换电站
                if node not in data.customer_ids: 
                    continue 
                
                # 遍历所有可能的目标车辆
                for r2_idx in range(len(solution)):
                    route2 = solution[r2_idx]
                    
                    # 遍历目标车辆的所有可能插入位置
                    for j in range(1, len(route2)):
                        # 如果是同一辆车，避免插入到它原本的位置或紧挨着的后面（无意义操作）
                        if r1_idx == r2_idx and (j == i or j == i + 1):
                            continue
                            
                        # 构造深拷贝的临时解，避免污染原解
                        temp_solution = deepcopy(solution)
                        
                        if r1_idx == r2_idx:
                            # 1. 同车内部移动
                            temp_r = temp_solution[r1_idx]
                            temp_r.pop(i)
                            insert_pos = j if j <= i else j - 1
                            temp_r.insert(insert_pos, node)
                            
                            is_feasible, _ = route_feasibility_check(data, cfg, temp_r)
                            if is_feasible:
                                new_cost = solution_cost(data, cfg, temp_solution)
                                if new_cost < current_cost:
                                    solution[:] = temp_solution
                                    improved = True
                                    break
                        else:
                            # 2. 跨车移动 (重点！)
                            temp_r1 = temp_solution[r1_idx]
                            temp_r2 = temp_solution[r2_idx]
                            
                            # 从源车拔出，插入目标车
                            temp_r1.pop(i)
                            temp_r2.insert(j, node)
                            
                            # 检查源车（少了一个点，大概率可行，但也可能因减载导致能耗变化，需严谨检查）
                            r1_feasible, _ = route_feasibility_check(data, cfg, temp_r1)
                            # 检查目标车
                            r2_feasible, _ = route_feasibility_check(data, cfg, temp_r2)
                            
                            # 🎯 核心逻辑：如果源车可行，但目标车不可行（大概率是电量超标），尝试用换电站抢救！
                            if r1_feasible and not r2_feasible:
                                success, adjusted_r2 = adjust_charge_stations(data, cfg, temp_r2)
                                if success and route_feasibility_check(data, cfg, adjusted_r2)[0]:
                                    temp_solution[r2_idx] = adjusted_r2
                                    r2_feasible = True
                            
                            # 如果两辆车最终都可行，评估成本
                            if r1_feasible and r2_feasible:
                                new_cost = solution_cost(data, cfg, temp_solution)
                                # 如果成本下降（比如成功消灭了一辆车的固定成本，或缩短了总距离）
                                if new_cost < current_cost:
                                    solution[:] = temp_solution
                                    improved = True
                                    break
                                    
                    if improved: break # 发现改进，立即跳出目标车插入点循环
                if improved: break # 跳出目标车循环
            if improved: break # 跳出源车节点循环
            
    return solution