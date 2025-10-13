from .initial_solution import generate_initial_solution
from .operators.destroy_ops import DESTROY_OPERATORS
from .operators.repair_ops import REPAIR_OPERATORS
from .utils.helpers import route_feasibility_check,solution_cost
from .utils.adaptive import select_operator, update_weights, acceptance_criterion, temperature

class ALNSSolver:
    def __init__(self, data, config):
        self.data = data
        self.cfg = config
        self.destroy_ops = DESTROY_OPERATORS
        self.repair_ops = REPAIR_OPERATORS
        self.destroy_weights = [5, 20]
        self.repair_weights = [10, 10]
        self.best_solution = None
        self.current_solution = None

    def solve(self):
        self.current_solution = generate_initial_solution(self.data, self.cfg)
        self.best_solution = self.current_solution.copy()

        for iter in range(self.cfg.max_iter):
            d_idx = select_operator(self.destroy_weights)
            r_idx = select_operator(self.repair_weights)
            destroyed, removed = self.destroy_ops[d_idx](self.data, self.current_solution)
            new_solution = self.repair_ops[r_idx](self.data, self.cfg, destroyed, removed)

            curr_cost = solution_cost(self.data, self.cfg, self.current_solution)
            new_cost = solution_cost(self.data, self.cfg, new_solution)

            update_weights(self.destroy_weights, self.repair_weights, d_idx, r_idx, new_cost - curr_cost)
            if acceptance_criterion(new_cost, curr_cost, temperature(iter)):
                self.current_solution = new_solution
                if new_cost < solution_cost(self.data, self.cfg, self.best_solution):
                    self.best_solution = new_solution

        return self.best_solution
