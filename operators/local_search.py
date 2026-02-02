from ..utils.helpers import route_feasibility_check, solution_cost

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