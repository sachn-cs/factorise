from factorise.core import is_prime

# Known primes
P31 = 2**31 - 1
P61 = 2**61 - 1
P47_CANDIDATE = 2**47 - 115

print(f"P31 is prime: {is_prime(P31)}")
print(f"P61 is prime: {is_prime(P61)}")
print(f"P47_CANDIDATE is prime: {is_prime(P47_CANDIDATE)}")

# Let's find a prime near 2^43
for i in range(2**43 - 1, 0, -1):
    if is_prime(i):
        print(f"P43: {i}")
        break
