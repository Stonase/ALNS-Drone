from .initial_solution import generate_initial_solution
from .operators.destroy_ops import DESTROY_OPERATORS
from .operators.repair_ops import REPAIR_OPERATORS
from .operators.local_search import local_search_2opt, local_search_prune_stations
from .utils.helpers import solution_cost, handle_unassigned_customers, rearrange_empty_vehicles
from .utils.adaptive import select_operator, update_weights, acceptance_criterion, temperature

class ALNSSolver:
    def __init__(self, data, config):
        self.data = data
        self.cfg = config
        self.destroy_ops = DESTROY_OPERATORS
        self.repair_ops = REPAIR_OPERATORS
        self.destroy_weights = [5, 20, 0]
        self.repair_weights = [10, 10]
        self.best_solution = None
        self.current_solution = None
        self.history = [] # 用于记录每轮的最佳成本

    def solve(self):
        self.current_solution = generate_initial_solution(self.data, self.cfg)
        self.best_solution = self.current_solution.copy()
        # 记录初始成本
        self.history.append(solution_cost(self.data, self.cfg, self.best_solution))

        for iter in range(self.cfg.max_iter):
            d_idx = select_operator(self.destroy_weights)
            r_idx = select_operator(self.repair_weights)
            destroyed, removed = self.destroy_ops[d_idx](self.data, self.cfg, self.current_solution)
            new_solution = self.repair_ops[r_idx](self.data, self.cfg, destroyed, removed)

            new_solution = local_search_2opt(self.data, self.cfg, new_solution)
            new_solution = local_search_prune_stations(self.data, self.cfg, new_solution)

            #解的后处理（含重新排列解）
            new_solution, has_unassigned = handle_unassigned_customers(self.data, self.cfg, new_solution)
            if has_unassigned:
                print(f"迭代{iter}：存在未分配客户，无人机资源不足")
                return self.current_solution
            new_solution = rearrange_empty_vehicles(new_solution)

            curr_cost = solution_cost(self.data, self.cfg, self.current_solution)
            new_cost = solution_cost(self.data, self.cfg, new_solution)
            
            self.history.append(solution_cost(self.data, self.cfg, self.best_solution))

            update_weights(self.destroy_weights, self.repair_weights, d_idx, r_idx, new_cost - curr_cost)
            if acceptance_criterion(new_cost, curr_cost, temperature(iter)):
                self.current_solution = new_solution
                if new_cost < solution_cost(self.data, self.cfg, self.best_solution):
                    self.best_solution = new_solution
        
        print(f"算法结束，共迭代 {self.cfg.max_iter} 次，最终最佳成本为 {solution_cost(self.data, self.cfg, self.best_solution):.2f}")

        return self.best_solution
