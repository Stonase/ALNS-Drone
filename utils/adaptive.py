import random, math

def select_operator(weights):
    total = sum(weights)
    r = random.uniform(0, total)
    acc = 0
    for i, w in enumerate(weights):
        acc += w
        if r <= acc:
            return i
    return len(weights) - 1

def update_weights(destroy_w, repair_w, di, ri, improvement):
    if improvement > 0:
        destroy_w[di] *= 1.02
        repair_w[ri] *= 1.02
    else:
        destroy_w[di] *= 0.9
        repair_w[ri] *= 0.9

def temperature(iteration):
    return 1000.0 * (0.95 ** iteration)

def acceptance_criterion(new_cost, current_cost, temp):
    return (new_cost < current_cost) or (random.random() < math.exp((current_cost - new_cost)/temp))
