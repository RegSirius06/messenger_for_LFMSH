import random

a = []

for i in range(0, 107):
    a.append(str(input()))

for i in range(10000):
    x = random.randint(0, 106)
    y = random.randint(0, 106)
    a[x], a[y] = a[y], a[x]

print(*a, sep=' - ')