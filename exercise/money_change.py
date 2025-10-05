import os
import json
import time

L = [5, 2, 1, 0.5, 0.2, 0.1, 0.05]
L.sort(reverse=True)
m = 12.35

# ------------------------------
# Greedy solution
def greedy_change(L, m):
    result = []
    for coin in L:
        count = int(m // coin)
        if count > 0:
            result.append({"coin": coin, "count": count})
            m = round(m - coin * count, 2)
    return result

# ------------------------------
# All solutions
all_solutions_iterations = 0
def all_solutions(L, m, i=0):
    global all_solutions_iterations
    all_solutions_iterations += 1

    if abs(m) < 1e-9:
        return [[]]
    if i >= len(L):
        return []
    coin = L[i]
    max_use = int(m // coin)
    solutions = []
    for k in range(max_use + 1):
        remainder = round(m - k * coin, 2)
        for rest in all_solutions(L, remainder, i+1):
            sol = []
            if k > 0:
                sol.append({"coin": coin, "count": k})
            sol.extend(rest)
            solutions.append(sol)
    return solutions

# ------------------------------
# First solution
first_iterations = 0
def first_solution(L, m):
    global first_iterations
    first_iterations += 1
    for i, coin in enumerate(L):
        count = int(m // coin)
        if count > 0:
            remainder = round(m - coin * count, 2)
            if abs(remainder) < 1e-9:
                return [{"coin": coin, "count": count}]
            else:
                rest = first_solution(L[i+1:], remainder)
                if rest is not None:
                    return [{"coin": coin, "count": count}] + rest
    return None

# ------------------------------
# Recursive change
recursive_iterations = 0
def recursive_change(L, m, i=0):
    global recursive_iterations
    recursive_iterations += 1

    if abs(m) < 1e-9:
        return []
    if i >= len(L):
        return None
    coin = L[i]
    count = int(m // coin)
    if count > 0:
        remainder = round(m - count * coin, 2)
        res = recursive_change(L, remainder, i+1)
        if res is not None:
            return [{"coin": coin, "count": count}] + res
    return recursive_change(L, m, i+1)

# ------------------------------
# Recursive best solution
best_solution_full = None
full_cut_iterations = 0

def recursive_change_best(L, m, i=0, current=[]):
    global best_solution_full, full_cut_iterations
    full_cut_iterations += 1

    if abs(m) < 1e-9:
        total_coins = sum(c["count"] for c in current)
        if (best_solution_full is None) or (total_coins < sum(c["count"] for c in best_solution_full)):
            best_solution_full = current.copy()
        return

    if i >= len(L):
        return

    coin = L[i]
    max_count = int(m // coin)

    for count in range(max_count, -1, -1):
        remainder = round(m - coin * count, 2)
        if best_solution_full is not None and sum(c["count"] for c in current) + count >= sum(c["count"] for c in best_solution_full):
            continue
        recursive_change_best(L, remainder, i+1, current + ([{"coin": coin, "count": count}] if count > 0 else []))

# ------------------------------
# Compute results with timing
results = {}

start_time = time.time()
greedy_sol = greedy_change(L, m)
results["Greedy"] = {
    "solutions": greedy_sol,
    "number_of_solutions": 1,
    "iterations": len(L),
    "execution_time_sec": time.time() - start_time
}

start_time = time.time()
all_sols = all_solutions(L, m)
results["All_solutions"] = {
    "solutions": all_sols,
    "number_of_solutions": len(all_sols),
    "iterations": all_solutions_iterations - 1,
    "execution_time_sec": time.time() - start_time
}

start_time = time.time()
first_sol = first_solution(L, m)
results["First_solution"] = {
    "solutions": first_sol,
    "number_of_solutions": 1,
    "iterations": first_iterations - 1,
    "execution_time_sec": time.time() - start_time
}

start_time = time.time()
recursive_sol = recursive_change(L, m)
results["Recursive_solution"] = {
    "solutions": recursive_sol,
    "number_of_solutions": 1,
    "iterations": recursive_iterations - 1,
    "execution_time_sec": time.time() - start_time
}

start_time = time.time()
best_solution_full = None
full_cut_iterations = 0
recursive_change_best(L, m)
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

