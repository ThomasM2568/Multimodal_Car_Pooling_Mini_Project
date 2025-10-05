matrices = [
    [   
        [1, 1, 1],
        [0, 0, 1],
        [1, 0, 0]
    ],
    [   
        [0, 1, 0],
        [0, 0, 1],
        [1, 0, 0]
    ]
]

def is_transitive(matrix):
    n = len(matrix)
    for i in range(n):
        for j in range(n):
            if matrix[i][j]:
                for k in range(n):
                    if matrix[j][k] and not matrix[i][k]:
                        return False
    return True

def is_irreflexive(matrix):
    return all(matrix[i][i] == 0 for i in range(len(matrix)))

def is_asymmetrical(matrix):
    n = len(matrix)
    for i in range(n):
        for j in range(n):
            if matrix[i][j] and matrix[j][i]:
                return False
    return True

def is_strictly_intransitive(matrix):
    n = len(matrix)
    for i in range(n):
        for j in range(n):
            if matrix[i][j]:
                for k in range(n):
                    if matrix[j][k] and matrix[i][k]:
                        return False
    return True

for idx, m in enumerate(matrices, start=1):
    print(f"\nMatrice {idx} :")
    for row in m:
        print(row)
    
    trans_status = "transitive" if is_transitive(m) else "non-transitive"
    irref_status = "irreflexive" if is_irreflexive(m) else "not irreflexive"
    asym_status = "asymmetrical" if is_asymmetrical(m) else "not asymmetrical"
    intrans_status = "strictly intransitive" if is_strictly_intransitive(m) else "not strictly intransitive"
    
    print(f"Result: {trans_status}, {irref_status}, {asym_status}, {intrans_status}")

