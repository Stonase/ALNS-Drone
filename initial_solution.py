import copy
from .utils.helpers import route_feasibility_check,solution_cost,charging_insert

def generate_initial_solution(data, cfg):
    depot = data.depot_id
    routes = [[depot, depot] for _ in range(cfg.vehicle_num)]
    must_insert_after = [0] * cfg.vehicle_num
    remaining = data.customer_ids.copy()
    used_vehicle_count = 1

    while remaining:
        sorted_customers = nearest_neighbor_sort(data, remaining, depot)
        if routes[used_vehicle_count-1]==[depot,depot]:
            routes[used_vehicle_count-1].insert(1, sorted_customers[0])
            remaining.remove(sorted_customers[0])
            sorted_customers.remove(sorted_customers[0])
        for cust in sorted_customers.copy():
            testing_resetcust = True
            testing_resetall = False
            while testing_resetcust:
                best_cost, best_route, best_pos,best_bat_ratio = float('inf'), None, None, None
                # 遍历所有已用车辆，寻找最优插入位置
                for route_idx in range(used_vehicle_count):
                    route = routes[route_idx]
                    start_pos = must_insert_after[route_idx]
                    for pos in range(start_pos, len(route)):
                        new_route = route[:pos] + [cust] + route[pos:]
                        # route_demand = sum(data.demands[n] for n in routes[best_route] if n in data.customer_ids)
                        feasible, bat_ratio = route_feasibility_check(data, cfg, new_route)
                        if feasible:
                            routes_tmp = copy.deepcopy(routes)
                            routes_tmp[route_idx] = new_route
                            cost = solution_cost(data, cfg, routes_tmp)
                            if cost < best_cost:
                                best_cost, best_route, best_pos, best_bat_ratio = cost, route_idx, pos, bat_ratio

                # 有可以插的位置就把客户插进去
                if best_route is not None:
                    # 插入客户
                    routes[best_route].insert(best_pos, cust)
                    remaining.remove(cust)

                    # 如果电量低于阈值，尝试在该路线插入最近换电站
                    low_thresh = cfg.low_battery_threshold
                    if best_bat_ratio is not None and best_bat_ratio < low_thresh:
                        success, new_route = charging_insert(data, cfg, routes[best_route])
                        if success:
                            routes[best_route] = new_route
                            cs_ids = set(data.charge_ids)          # 转成集合，查找 O(1)
                            reverse = new_route[::-1]
                            rev_idx = next(i for i, node in enumerate(reverse) if node in cs_ids)
                            cs_pos = len(new_route) - 1 - rev_idx
                            must_insert_after[best_route] = cs_pos
                    break

                else:
                    # 无法插入到任何已用车辆
                    # if bat_ratio is not None and bat_ratio < 0.1:
                    #     # 电量不足，尝试对已有路线插入换电站以腾出可行空间
                    #     success, new_route = charging_insert(data, cfg, routes[used_vehicle_count-1])
                    #     if success:
                    #         routes[used_vehicle_count-1] = new_route
                    #         continue

                    if used_vehicle_count < cfg.vehicle_num:
                        # 启用新车并插入
                        # routes[used_vehicle_count].insert(1, cust)
                        # remaining.remove(cust)
                        used_vehicle_count += 1
                        testing_resetall = True
                        break
                    else:
                        # 没有备用车辆，尝试对已有路线插入换电站以腾出可行空间
                        inserted = False
                        for ridx in range(used_vehicle_count):
                            success, tmp_route = charging_insert(data, cfg, routes[ridx])
                            if success:
                                best_cost, best_pos = float('inf'), None
                                for pos in range(1, len(route)):
                                    new_route = tmp_route[:pos] + [cust] + tmp_route[pos:]
                                    # route_demand = sum(data.demands[n] for n in routes[best_route] if n in data.customer_ids)
                                    feasible, _ = route_feasibility_check(data, cfg, new_route)
                                    if feasible:
                                        cost = solution_cost(data, cfg, [new_route])
                                        if cost < best_cost:
                                            best_cost, best_pos = cost, route_idx

                                # 有可以插的位置就把客户插进去
                                if best_pos is not None:
                                    # 插入客户
                                    tmp_route.insert(best_pos, cust)
                                    routes[ridx] = tmp_route
                                    remaining.remove(cust)
                                    break
                                else:
                                    raise ValueError(f"客户 {cust} 无法分配，且无可用车辆或换电站插入失败")
                                
                                # routes[ridx] = new_route
                                # inserted = True
                                # testing_resetall = True
                                # break
                        # if inserted:
                        #     # 进行了换电站插入，让外层循环重新尝试分配当前客户
                        #     continue                    
            if testing_resetall:
                break
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
