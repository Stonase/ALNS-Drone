import random
import copy
from .utils.helpers import solution_cost, route_feasibility_check, charging_insert

class GASolver:
    def __init__(self, data, config):
        self.data = data
        self.cfg = config
        
        # GA 专属超参数设定 (可按需调节)
        self.pop_size = 50                 # 种群大小
        self.generations = getattr(config, 'max_iter', 100)  # 迭代次数，与ALNS使用相同配置对比
        self.crossover_rate = 0.8          # 交叉概率
        self.mutation_rate = 0.2           # 变异概率
        self.tournament_size = 3           # 锦标赛选择规模
        
        self.best_solution = None
        self.best_cost = float('inf')

    def decode(self, giant_tour):
        """
        解码：将一条客户点的全排列（巨型路线）切割成多台无人机的有效路径
        并复用你的 helpers.py 中的可行性与换电站插入逻辑
        """
        routes = []
        current_route = [self.data.depot_id]
        
        for cust in giant_tour:
            # 试探性将客户加入当前车辆
            test_route = current_route + [cust, self.data.depot_id]
            feasible, _ = route_feasibility_check(self.data, self.cfg, test_route)
            
            if feasible:
                current_route.append(cust)
            else:
                # 若不可行，尝试让复用你的修复逻辑插入换电站
                success, repaired_route = charging_insert(self.data, self.cfg, test_route)
                
                if success:
                    # 插入换电站成功！repaired_route 结尾包含车场，我们需要去除末尾车场以便继续添加客户
                    current_route = repaired_route[:-1]
                else:
                    # 无法通过插入换电站解决（可能超载），当前车辆封车，开派新车
                    if len(current_route) > 1:
                        current_route.append(self.data.depot_id)
                        routes.append(current_route)
                    current_route = [self.data.depot_id, cust]
        
        # 封存最后一辆车
        if len(current_route) > 1:
            current_route.append(self.data.depot_id)
            routes.append(current_route)
            
        # 填补空车以满足 config 中固定的车辆总数
        while len(routes) < self.cfg.vehicle_num:
            routes.append([self.data.depot_id, self.data.depot_id])
            
        return routes

    def evaluate(self, population):
        """评估种群适应度，惩罚超出车辆数限制的解"""
        scored_pop = []
        for ind in population:
            routes = self.decode(ind)
            
            # 计算客观成本
            cost = solution_cost(self.data, self.cfg, routes)
            
            # 软约束硬惩罚：如果调用的车辆大于可用车辆数，给予巨额惩罚
            used_vehicles = sum(1 for r in routes if len(r) > 2)
            if used_vehicles > self.cfg.vehicle_num:
                cost += (used_vehicles - self.cfg.vehicle_num) * 10000 
            
            scored_pop.append({'chromosome': ind, 'cost': cost, 'routes': routes})
            
            # 记录全局最优 (只有合法解才记录)
            if cost < self.best_cost and used_vehicles <= self.cfg.vehicle_num:
                self.best_cost = cost
                self.best_solution = copy.deepcopy(routes)
                
        return scored_pop

    def tournament_selection(self, scored_pop):
        """选择算子：锦标赛选择法"""
        competitors = random.sample(scored_pop, self.tournament_size)
        competitors.sort(key=lambda x: x['cost'])
        return competitors[0]['chromosome']

    def order_crossover(self, p1, p2):
        """交叉算子：针对排列组合的顺序交叉 (Order Crossover, OX1)"""
        size = len(p1)
        c1, c2 = [-1]*size, [-1]*size
        
        # 随机截取两点作为交叉片段
        start, end = sorted(random.sample(range(size), 2))
        
        c1[start:end+1] = p1[start:end+1]
        c2[start:end+1] = p2[start:end+1]
        
        # 填补剩余基因，保证客户点不重复
        def fill_gene(child, parent):
            p_idx = (end + 1) % size
            c_idx = (end + 1) % size
            while -1 in child:
                if parent[p_idx] not in child:
                    child[c_idx] = parent[p_idx]
                    c_idx = (c_idx + 1) % size
                p_idx = (p_idx + 1) % size
                
        fill_gene(c1, p2)
        fill_gene(c2, p1)
        return c1, c2

    def mutate(self, chromosome):
        """变异算子：随机交换位置 (Swap) 或 逆序互换 (Inversion)"""
        if random.random() < self.mutation_rate:
            if random.random() < 0.5:
                # 两点交换
                idx1, idx2 = random.sample(range(len(chromosome)), 2)
                chromosome[idx1], chromosome[idx2] = chromosome[idx2], chromosome[idx1]
            else:
                # 逆序片段
                idx1, idx2 = sorted(random.sample(range(len(chromosome)), 2))
                chromosome[idx1:idx2+1] = reversed(chromosome[idx1:idx2+1])

    def solve(self):
        """对外暴露的求解入口，与 ALNSSolver 保持相同的调用习惯"""
        print(">>> 启动遗传算法 (GA) 求解器...")
        
        # 1. 初始化种群 (随机打乱所有客户点)
        population = []
        customer_list = list(self.data.customer_ids)
        for _ in range(self.pop_size):
            ind = copy.copy(customer_list)
            random.shuffle(ind)
            population.append(ind)
            
        # 2. 演化迭代
        for gen in range(self.generations):
            scored_pop = self.evaluate(population)
            
            # 按成本升序排列
            scored_pop.sort(key=lambda x: x['cost'])
            
            # 精英保留 (Elitism)：保留当代最佳的2个个体直接进入下一代
            new_population = [scored_pop[0]['chromosome'], scored_pop[1]['chromosome']]
            
            # 繁衍下一代
            while len(new_population) < self.pop_size:
                p1 = self.tournament_selection(scored_pop)
                p2 = self.tournament_selection(scored_pop)
                
                if random.random() < self.crossover_rate:
                    c1, c2 = self.order_crossover(p1, p2)
                else:
                    c1, c2 = copy.copy(p1), copy.copy(p2)
                    
                self.mutate(c1)
                self.mutate(c2)
                
                new_population.extend([c1, c2])
                
            population = new_population[:self.pop_size]
            
            # 打印收敛过程
            if gen % 10 == 0 or gen == self.generations - 1:
                print(f"GA 第 {gen} 代：当前最优总成本 = {self.best_cost:.2f}")
                
        # 最终可能会产生空缺客户问题（极少情况），可套用您的后处理防抖
        from .utils.helpers import handle_unassigned_customers
        self.best_solution, _ = handle_unassigned_customers(self.data, self.cfg, self.best_solution)
        
        return self.best_solution