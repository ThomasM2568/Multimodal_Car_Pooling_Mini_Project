import os
import json
import time

L = [5, 2, 1, 0.5, 0.2, 0.1, 0.05]
L.sort(reverse=True)
m = 12.35

# Define maximum allowed coins per denomination (adjust as needed)
max_per_coin = {
    5: 1,
    2: 15,
    1: 5,
    0.5: 4,
    0.2: 10,
    0.1: 10,
    0.05: 20
}

# ------------------------------
# Greedy solution with max constraint
def greedy_change(L, m, max_per_coin):
    result = []
    for coin in L:
        count = int(m // coin)
        if coin in max_per_coin:
            count = min(count, max_per_coin[coin])  # apply max constraint
        if count > 0:
            result.append((coin, count))
            m = round(m - coin * count, 2)
    return result

# ------------------------------
# All solutions with max constraint
all_solutions_iterations = 0
def all_solutions(L, m, i=0, max_per_coin=None):
    global all_solutions_iterations
    all_solutions_iterations += 1

    if abs(m) < 1e-9:
        return [[]]
    if i >= len(L):
        return []

    coin = L[i]
    max_use = int(m // coin)
    if max_per_coin and coin in max_per_coin:
        max_use = min(max_use, max_per_coin[coin])  # apply max constraint

    solutions = []
    for k in range(max_use + 1):
        remainder = round(m - k * coin, 2)
        for rest in all_solutions(L, remainder, i+1, max_per_coin):
            sol = []
            if k > 0:
                sol.append((coin, k))
            sol.extend(rest)
            solutions.append(sol)
    return solutions

# ------------------------------
# First solution with max constraint
first_iterations = 0
def first_solution(L, m, max_per_coin=None):
    global first_iterations
    first_iterations += 1
    for i, coin in enumerate(L):
        count = int(m // coin)
        if max_per_coin and coin in max_per_coin:
            count = min(count, max_per_coin[coin])
        if count > 0:
            remainder = round(m - coin * count, 2)
            if abs(remainder) < 1e-9:
                return [(coin, count)]
            else:
                rest = first_solution(L[i+1:], remainder, max_per_coin)
                if rest is not None:
                    return [(coin, count)] + rest
    return None

# ------------------------------
# Recursive change with max constraint
recursive_iterations = 0
def recursive_change(L, m, i=0, max_per_coin=None):
    global recursive_iterations
    recursive_iterations += 1

    if abs(m) < 1e-9:
        return []
    if i >= len(L):
        return None

    coin = L[i]
    count = int(m // coin)
    if max_per_coin and coin in max_per_coin:
        count = min(count, max_per_coin[coin])

    if count > 0:
        remainder = round(m - count * coin, 2)
        res = recursive_change(L, remainder, i+1, max_per_coin)
        if res is not None:
            return [(coin, count)] + res
    return recursive_change(L, m, i+1, max_per_coin)

# ------------------------------
# Recursive best with max constraint
best_solution_full = None
full_cut_iterations = 0

def recursive_change_best(L, m, i=0, current=[], max_per_coin=None):
    global best_solution_full, full_cut_iterations
    full_cut_iterations += 1

    if abs(m) < 1e-9:
        total_coins = sum(c for _, c in current)
        if (best_solution_full is None) or (total_coins < sum(c for _, c in best_solution_full)):
            best_solution_full = current.copy()
        return

    if i >= len(L):
        return

    coin = L[i]
    max_count = int(m // coin)
    if max_per_coin and coin in max_per_coin:
        max_count = min(max_count, max_per_coin[coin])

    for count in range(max_count, -1, -1):
        remainder = round(m - coin * count, 2)
        if best_solution_full is not None and sum(c for _, c in current) + count >= sum(c for _, c in best_solution_full):
            continue
        recursive_change_best(L, remainder, i+1, current + ([(coin, count)] if count > 0 else []), max_per_coin)

# ------------------------------
# Compute results with timing
results = {}

start_time = time.time()
greedy_sol = greedy_change(L, m, max_per_coin)
results["Greedy"] = {
    "solutions": greedy_sol,
    "number_of_solutions": 1,
    "iterations": len(L),
    "execution_time_sec": time.time() - start_time
}

start_time = time.time()
all_sols = all_solutions(L, m, 0, max_per_coin)
results["All_solutions"] = {
    "solutions": all_sols,
    "number_of_solutions": len(all_sols),
    "iterations": all_solutions_iterations - 1,
    "execution_time_sec": time.time() - start_time
}

start_time = time.time()
first_sol = first_solution(L, m, max_per_coin)
results["First_solution"] = {
    "solutions": first_sol,
    "number_of_solutions": 1 if first_sol else 0,
    "iterations": first_iterations - 1,
    "execution_time_sec": time.time() - start_time
}

start_time = time.time()
recursive_sol = recursive_change(L, m, 0, max_per_coin)
results["Recursive_solution"] = {
    "solutions": recursive_sol,
    "number_of_solutions": 1 if recursive_sol else 0,
    "iterations": recursive_iterations - 1,
    "execution_time_sec": time.time() - start_time
}

start_time = time.time()
best_solution_full = None
full_cut_iterations = 0
recursive_change_best(L, m, 0, [], max_per_coin)
results["Recursive_best_solution"] = {
    "solutions": best_solution_full,
    "number_of_solutions": 1 if best_solution_full else 0,
    "iterations": full_cut_iterations,
    "execution_time_sec": time.time() - start_time
}

# ------------------------------
# Save JSON
file_name = "coin_change_results.json"
full_path = os.path.abspath(file_name)

with open(full_path, "w") as f:
    json.dump(results, f, indent=4)

print("Results saved to: \n", full_path)
