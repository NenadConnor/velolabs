"""Deterministic Halton sampling, with no RNG or external optimizer dependency."""
def radical_inverse(index: int, base: int) -> float:
    fraction, value = 1.0, 0.0
    while index:
        fraction /= base
        index, digit = divmod(index, base)
        value += digit * fraction
    return value
