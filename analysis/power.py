#!/usr/bin/env python3
"""Power of the directional test: n calls, two-sided alpha=0.05 vs p=0.5, 80% power. Stdlib only, deterministic.

Usage: python3 analysis/power.py [n]     (default n=34, the number of directional calls)
"""
import math
import sys
from statistics import NormalDist

sys.path.insert(0, __file__.rsplit('/analysis/', 1)[0])
from baseline import binom_two_sided_p  # same exact test the paper uses

N01 = NormalDist()


def exact_power(n, p, alpha=0.05):
    """P(reject H0: p=0.5) when the true accuracy is p, using the exact two-sided binomial test."""
    pmf = lambda k: math.comb(n, k) * p**k * (1 - p)**(n - k)
    return sum(pmf(k) for k in range(n + 1) if binom_two_sided_p(k, n) <= alpha)


def normal_power(n, p, alpha=0.05):
    z, s0, s1 = N01.inv_cdf(1 - alpha / 2), math.sqrt(.25 / n), math.sqrt(p * (1 - p) / n)
    d = p - .5
    return N01.cdf((d - z * s0) / s1) + N01.cdf((-d - z * s0) / s1)


def min_p(fn, n, target=0.8):
    # linear scan: exact power is a sawtooth in p, so bisection is unsafe
    return next(round(i / 1000, 3) for i in range(501, 1001) if fn(n, i / 1000) >= target)


def main(n):
    print(f"n = {n} directional calls, alpha = 0.05 two-sided, target power 80%")
    print(f"  normal approximation: need true accuracy >= {min_p(normal_power, n):.3f}")
    print(f"  simple null-variance formula 0.5 + (1.96+0.84)*0.5/sqrt(n) = {0.5 + (1.96 + 0.8416) * 0.5 / math.sqrt(n):.3f}")
    print(f"  exact binomial test:  need true accuracy >= {min_p(exact_power, n):.3f}")
    print(f"  (the exact test's actual size at p=0.5 is {exact_power(n, .5):.3f}; discreteness makes it conservative)")
    for p in (.60, .65, .70):
        print(f"  power if true accuracy = {p:.2f}: exact {exact_power(n, p):.2f}, normal {normal_power(n, p):.2f}")


def _demo():
    assert exact_power(34, .5) <= 0.05 + 1e-9
    assert exact_power(34, .9) > 0.99 and exact_power(34, .55) < exact_power(34, .75)
    print('self-check passed')


if __name__ == '__main__':
    _demo() if '--test' in sys.argv else main(int(sys.argv[1]) if len(sys.argv) > 1 else 34)
