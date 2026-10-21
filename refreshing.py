"""Exact scalar reference algorithms for current-observation refreshing.

Copyright (c) 2026 Hiroyasu Usami. SPDX-License-Identifier: MIT
"""
from fractions import Fraction as Q

COUNTS = {}

class CheckFailure(Exception):
    def __init__(self, label, case):
        self.label, self.case = label, case
        super().__init__(label)


def check(condition, label, **case):
    if not condition:
        raise CheckFailure(label, case)
    COUNTS[label] = COUNTS.get(label, 0) + 1


def serial(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, (tuple, list)):
        return [serial(v) for v in value]
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in value.items()}
    return value


def variation(path):
    return sum((abs(b-a) for a, b in zip(path, path[1:])), Q(0))


def schedule_cost(path, starts, lam):
    """Post-decision discrepancy; initial refresh at index zero is charged."""
    if not starts or starts[0] != 0:
        raise CheckFailure('invalid schedule initialization', {'starts': starts})
    cache = 0
    distortion = Q(0)
    chosen = set(starts)
    for t, value in enumerate(path):
        if t in chosen:
            cache = t
        distortion += abs(value-path[cache])
    return distortion + lam*len(starts), distortion


def all_segmentations(path):
    """Independent direct cache replay for all 2**(T-1) refresh subsets."""
    T = len(path)
    for mask in range(1 << (T-1)):
        starts = [0] + [t for t in range(1, T) if mask & (1 << (t-1))]
        _, distortion = schedule_cost(path, starts, Q(0))
        yield len(starts), distortion, starts


def frontier_dp(path, lam, canonical=False):
    """Exact oracle with O(T) auxiliary arrays, in addition to the input path.

    On extending u, segment_sum[s] adds d(z[u-1],z[s]). Cost-only execution
    uses O(T**2) distance evaluations/arithmetic operations if those primitives
    have unit cost. Fraction bit costs and high-dimensional distance costs
    are not unit cost. Optional canonical tie recovery below adds temporary
    O(T) lists and can add time on ties; it is not the cost-only time claim.
    """
    T = len(path)
    segment_sum = [Q(0)]*T
    D = [Q(0)] + [None]*T
    number = [0]*(T+1)
    parent = [-1]*(T+1)

    def previous_starts(u):
        result = []
        while u:
            s = parent[u]
            result.append(s)
            u = s
        return list(reversed(result))

    for u in range(1, T+1):
        best = None
        for s in range(u):
            segment_sum[s] += abs(path[u-1]-path[s])
            candidate = (D[s]+lam+segment_sum[s], number[s]+1, s)
            if best is None or candidate[:2] < best[:2]:
                best = candidate
            elif canonical and candidate[:2] == best[:2]:
                if previous_starts(s)+[s] < previous_starts(best[2])+[best[2]]:
                    best = candidate
        D[u], number[u], parent[u] = best
    starts = previous_starts(T)
    return D[T], number[T], starts


def run_policy(path, lam, kind):
    """No age cap. Compare squared nonnegative thresholds exactly; strict >."""
    if lam <= 0:
        raise ValueError('The anytime/clipped policy checks require lambda>0')
    T = len(path)
    if kind == 'clipped' and T < 2:
        raise ValueError('The clipped theorem assumes T>=2')
    V = variation(path)
    S = Q(0)
    cache = 0
    starts = [0]
    distortion = Q(0)
    trace = []
    for t in range(1, T):
        S += abs(path[t]-path[t-1])
        if kind == 'anytime':
            threshold2 = lam*S/t
        elif kind == 'fixed':
            threshold2 = lam*V/T
        elif kind == 'clipped':
            threshold2 = min(lam*lam, max((lam/T)**2, lam*S/T))
            # A separate piecewise evaluation checks both threshold joins.
            piecewise = ((lam/T)**2 if S <= lam/T else
                         lam*lam if S >= lam*T else lam*S/T)
            check(threshold2 == piecewise, 'clipped squared formula equals piecewise',
                  path=path, lam=lam, t=t)
        else:
            raise ValueError(kind)
        drift2 = (path[t]-path[cache])**2
        refresh = drift2 > threshold2
        if refresh:
            cache = t
            starts.append(t)
        post = abs(path[t]-path[cache])
        check(post*post <= threshold2, 'post-decision discrepancy within threshold',
              path=path, lam=lam, kind=kind, t=t)
        distortion += post
        trace.append({'t': t, 'S': S, 'threshold_squared': threshold2,
                      'pre_decision_drift_squared': drift2, 'refresh': refresh,
                      'post_decision_discrepancy': post})
    cost = distortion+lam*len(starts)
    check(schedule_cost(path, starts, lam)[0] == cost,
          'policy cost agrees with separate schedule replay', path=path, lam=lam, kind=kind)
    return {'cost': cost, 'distortion': distortion, 'count': len(starts),
            'starts': starts, 'trace': trace, 'V': V}


def check_policy_bounds(path, lam, kind):
    p = run_policy(path, lam, kind)
    T, V, J = len(path), p['V'], p['cost']
    if kind == 'anytime':
        # J <= lambda+4sqrt(lambda*T*V), without floating square roots.
        check(J <= lam or (J-lam)**2 <= 16*lam*T*V,
              'anytime theorem bound', path=path, lam=lam, policy=p)
    elif kind == 'clipped':
        A, B = lam*T, lam+(T-1)*V
        check(J <= lam*T, 'clipped global per-time cap',
              path=path, lam=lam, policy=p)
        check(J <= 3*A and J <= 3*B and
              (J <= 3*lam or (J-3*lam)**2 <= 36*lam*T*V),
              'clipped factor-three comparison', path=path, lam=lam, policy=p)
        if V <= lam/T:
            check(J <= B and p['count'] == 1,
                  'clipped small regime', path=path, lam=lam, policy=p)
        elif V <= lam*T:
            coefficient = Q(3)-Q(1,T)
            check(J*J < coefficient*coefficient*lam*T*V,
                  'clipped strict middle regime', path=path, lam=lam, policy=p)
        else:
            check(J <= T*lam,
                  'clipped large regime cap', path=path, lam=lam, policy=p)
    return p


def ramp_formula(T, n, slope, lam):
    q, r = divmod(T, n)
    return lam*n + slope*Q(r*q*(q+1)+(n-r)*q*(q-1), 2)
