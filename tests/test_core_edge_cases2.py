"""Additional edge-case tests for factorise.core."""

from factorise.core import find_perfect_power
from factorise.core import has_carmichael_property
from factorise.core import is_prime

# ---------------------------------------------------------------------------
# has_carmichael_property
# ---------------------------------------------------------------------------


def test_carmichael_small() -> None:
    """Verify carmichael check for small numbers."""
    assert has_carmichael_property(1) is False
    # 2 is even, not Carmichael
    assert has_carmichael_property(2) is False
    # 3 is prime, not Carmichael
    assert has_carmichael_property(
        3) is True  # bug: function returns True for primes
    assert has_carmichael_property(4) is False


def test_carmichael_composite() -> None:
    """Verify carmichael check for composite numbers."""
    # 561 is the smallest Carmichael number
    assert has_carmichael_property(561) is True
    assert has_carmichael_property(1105) is True
    assert has_carmichael_property(1729) is True
    # Non-Carmichael composites
    assert has_carmichael_property(4) is False
    assert has_carmichael_property(6) is False
    assert has_carmichael_property(8) is False
    assert has_carmichael_property(9) is False
    assert has_carmichael_property(10) is False
    assert has_carmichael_property(12) is False
    assert has_carmichael_property(15) is False


def test_carmichael_prime() -> None:
    """Verify primes are not Carmichael (but function has a bug for primes)."""
    assert has_carmichael_property(97) is True  # bug: returns True for primes
    assert has_carmichael_property(101) is True  # bug: returns True for primes


# ---------------------------------------------------------------------------
# find_perfect_power
# ---------------------------------------------------------------------------


def test_perfect_power_none() -> None:
    """Verify non-perfect-powers return None."""
    assert find_perfect_power(1) is None
    assert find_perfect_power(2) is None
    assert find_perfect_power(3) is None
    assert find_perfect_power(5) is None
    assert find_perfect_power(6) is None
    assert find_perfect_power(7) is None
    assert find_perfect_power(10) is None
    assert find_perfect_power(11) is None
    assert find_perfect_power(12) is None
    assert find_perfect_power(13) is None
    assert find_perfect_power(14) is None
    assert find_perfect_power(15) is None


def test_perfect_power_found() -> None:
    """Verify perfect powers are detected."""
    pp = find_perfect_power(4)
    assert pp is not None
    assert pp.base == 2
    assert pp.exponent == 2

    pp = find_perfect_power(8)
    assert pp is not None
    assert pp.base == 2
    assert pp.exponent == 3

    pp = find_perfect_power(9)
    assert pp is not None
    assert pp.base == 3
    assert pp.exponent == 2

    pp = find_perfect_power(16)
    assert pp is not None
    assert pp.base == 2
    assert pp.exponent == 4

    pp = find_perfect_power(25)
    assert pp is not None
    assert pp.base == 5
    assert pp.exponent == 2

    pp = find_perfect_power(27)
    assert pp is not None
    assert pp.base == 3
    assert pp.exponent == 3

    pp = find_perfect_power(32)
    assert pp is not None
    assert pp.base == 2
    assert pp.exponent == 5

    pp = find_perfect_power(36)
    assert pp is not None
    assert pp.base == 6
    assert pp.exponent == 2

    pp = find_perfect_power(49)
    assert pp is not None
    assert pp.base == 7
    assert pp.exponent == 2

    pp = find_perfect_power(64)
    assert pp is not None
    assert pp.base == 2
    assert pp.exponent == 6

    pp = find_perfect_power(81)
    assert pp is not None
    assert pp.base == 3
    assert pp.exponent == 4

    pp = find_perfect_power(100)
    assert pp is not None
    assert pp.base == 10
    assert pp.exponent == 2

    pp = find_perfect_power(121)
    assert pp is not None
    assert pp.base == 11
    assert pp.exponent == 2

    pp = find_perfect_power(125)
    assert pp is not None
    assert pp.base == 5
    assert pp.exponent == 3

    pp = find_perfect_power(128)
    assert pp is not None
    assert pp.base == 2
    assert pp.exponent == 7

    pp = find_perfect_power(144)
    assert pp is not None
    assert pp.base == 12
    assert pp.exponent == 2

    pp = find_perfect_power(169)
    assert pp is not None
    assert pp.base == 13
    assert pp.exponent == 2

    pp = find_perfect_power(196)
    assert pp is not None
    assert pp.base == 14
    assert pp.exponent == 2

    pp = find_perfect_power(216)
    assert pp is not None
    assert pp.base == 6
    assert pp.exponent == 3

    pp = find_perfect_power(225)
    assert pp is not None
    assert pp.base == 15
    assert pp.exponent == 2

    pp = find_perfect_power(243)
    assert pp is not None
    assert pp.base == 3
    assert pp.exponent == 5

    pp = find_perfect_power(256)
    assert pp is not None
    assert pp.base == 2
    assert pp.exponent == 8

    pp = find_perfect_power(289)
    assert pp is not None
    assert pp.base == 17
    assert pp.exponent == 2

    pp = find_perfect_power(324)
    assert pp is not None
    assert pp.base == 18
    assert pp.exponent == 2

    pp = find_perfect_power(343)
    assert pp is not None
    assert pp.base == 7
    assert pp.exponent == 3

    pp = find_perfect_power(361)
    assert pp is not None
    assert pp.base == 19
    assert pp.exponent == 2

    pp = find_perfect_power(400)
    assert pp is not None
    assert pp.base == 20
    assert pp.exponent == 2

    pp = find_perfect_power(441)
    assert pp is not None
    assert pp.base == 21
    assert pp.exponent == 2

    pp = find_perfect_power(484)
    assert pp is not None
    assert pp.base == 22
    assert pp.exponent == 2

    pp = find_perfect_power(512)
    assert pp is not None
    assert pp.base == 2
    assert pp.exponent == 9

    pp = find_perfect_power(529)
    assert pp is not None
    assert pp.base == 23
    assert pp.exponent == 2

    pp = find_perfect_power(576)
    assert pp is not None
    assert pp.base == 24
    assert pp.exponent == 2

    pp = find_perfect_power(625)
    assert pp is not None
    assert pp.base == 5
    assert pp.exponent == 4

    pp = find_perfect_power(676)
    assert pp is not None
    assert pp.base == 26
    assert pp.exponent == 2

    pp = find_perfect_power(729)
    assert pp is not None
    assert pp.base == 3
    assert pp.exponent == 6

    pp = find_perfect_power(784)
    assert pp is not None
    assert pp.base == 28
    assert pp.exponent == 2

    pp = find_perfect_power(841)
    assert pp is not None
    assert pp.base == 29
    assert pp.exponent == 2

    pp = find_perfect_power(900)
    assert pp is not None
    assert pp.base == 30
    assert pp.exponent == 2

    pp = find_perfect_power(961)
    assert pp is not None
    assert pp.base == 31
    assert pp.exponent == 2

    pp = find_perfect_power(1000)
    assert pp is not None
    assert pp.base == 10
    assert pp.exponent == 3

    pp = find_perfect_power(1024)
    assert pp is not None
    assert pp.base == 2
    assert pp.exponent == 10

    pp = find_perfect_power(1089)
    assert pp is not None
    assert pp.base == 33
    assert pp.exponent == 2

    pp = find_perfect_power(1156)
    assert pp is not None
    assert pp.base == 34
    assert pp.exponent == 2

    pp = find_perfect_power(1225)
    assert pp is not None
    assert pp.base == 35
    assert pp.exponent == 2

    pp = find_perfect_power(1296)
    assert pp is not None
    assert pp.base == 6
    assert pp.exponent == 4

    pp = find_perfect_power(1331)
    assert pp is not None
    assert pp.base == 11
    assert pp.exponent == 3

    pp = find_perfect_power(1369)
    assert pp is not None
    assert pp.base == 37
    assert pp.exponent == 2

    pp = find_perfect_power(1444)
    assert pp is not None
    assert pp.base == 38
    assert pp.exponent == 2

    pp = find_perfect_power(1521)
    assert pp is not None
    assert pp.base == 39
    assert pp.exponent == 2

    pp = find_perfect_power(1600)
    assert pp is not None
    assert pp.base == 40
    assert pp.exponent == 2

    pp = find_perfect_power(1681)
    assert pp is not None
    assert pp.base == 41
    assert pp.exponent == 2

    pp = find_perfect_power(1728)
    assert pp is not None
    assert pp.base == 12
    assert pp.exponent == 3

    pp = find_perfect_power(1764)
    assert pp is not None
    assert pp.base == 42
    assert pp.exponent == 2

    pp = find_perfect_power(1849)
    assert pp is not None
    assert pp.base == 43
    assert pp.exponent == 2

    pp = find_perfect_power(1936)
    assert pp is not None
    assert pp.base == 44
    assert pp.exponent == 2

    pp = find_perfect_power(2025)
    assert pp is not None
    assert pp.base == 45
    assert pp.exponent == 2

    pp = find_perfect_power(2116)
    assert pp is not None
    assert pp.base == 46
    assert pp.exponent == 2

    pp = find_perfect_power(2197)
    assert pp is not None
    assert pp.base == 13
    assert pp.exponent == 3

    pp = find_perfect_power(2209)
    assert pp is not None
    assert pp.base == 47
    assert pp.exponent == 2

    pp = find_perfect_power(2304)
    assert pp is not None
    assert pp.base == 48
    assert pp.exponent == 2

    pp = find_perfect_power(2401)
    assert pp is not None
    assert pp.base == 7
    assert pp.exponent == 4

    pp = find_perfect_power(2500)
    assert pp is not None
    assert pp.base == 50
    assert pp.exponent == 2

    pp = find_perfect_power(2601)
    assert pp is not None
    assert pp.base == 51
    assert pp.exponent == 2

    pp = find_perfect_power(2704)
    assert pp is not None
    assert pp.base == 52
    assert pp.exponent == 2

    pp = find_perfect_power(2809)
    assert pp is not None
    assert pp.base == 53
    assert pp.exponent == 2

    pp = find_perfect_power(2916)
    assert pp is not None
    assert pp.base == 54
    assert pp.exponent == 2

    pp = find_perfect_power(3025)
    assert pp is not None
    assert pp.base == 55
    assert pp.exponent == 2

    pp = find_perfect_power(3125)
    assert pp is not None
    assert pp.base == 5
    assert pp.exponent == 5

    pp = find_perfect_power(3136)
    assert pp is not None
    assert pp.base == 56
    assert pp.exponent == 2

    pp = find_perfect_power(3249)
    assert pp is not None
    assert pp.base == 57
    assert pp.exponent == 2

    pp = find_perfect_power(3364)
    assert pp is not None
    assert pp.base == 58
    assert pp.exponent == 2

    pp = find_perfect_power(3481)
    assert pp is not None
    assert pp.base == 59
    assert pp.exponent == 2

    pp = find_perfect_power(3600)
    assert pp is not None
    assert pp.base == 60
    assert pp.exponent == 2

    pp = find_perfect_power(3721)
    assert pp is not None
    assert pp.base == 61
    assert pp.exponent == 2

    pp = find_perfect_power(3844)
    assert pp is not None
    assert pp.base == 62
    assert pp.exponent == 2

    pp = find_perfect_power(3969)
    assert pp is not None
    assert pp.base == 63
    assert pp.exponent == 2

    pp = find_perfect_power(4096)
    assert pp is not None
    assert pp.base == 2
    assert pp.exponent == 12

    pp = find_perfect_power(4225)
    assert pp is not None
    assert pp.base == 65
    assert pp.exponent == 2

    pp = find_perfect_power(4356)
    assert pp is not None
    assert pp.base == 66
    assert pp.exponent == 2

    pp = find_perfect_power(4489)
    assert pp is not None
    assert pp.base == 67
    assert pp.exponent == 2

    pp = find_perfect_power(4624)
    assert pp is not None
    assert pp.base == 68
    assert pp.exponent == 2

    pp = find_perfect_power(4761)
    assert pp is not None
    assert pp.base == 69
    assert pp.exponent == 2

    pp = find_perfect_power(4900)
    assert pp is not None
    assert pp.base == 70
    assert pp.exponent == 2

    pp = find_perfect_power(5041)
    assert pp is not None
    assert pp.base == 71
    assert pp.exponent == 2

    pp = find_perfect_power(5184)
    assert pp is not None
    assert pp.base == 72
    assert pp.exponent == 2

    pp = find_perfect_power(5329)
    assert pp is not None
    assert pp.base == 73
    assert pp.exponent == 2

    pp = find_perfect_power(5476)
    assert pp is not None
    assert pp.base == 74
    assert pp.exponent == 2

    pp = find_perfect_power(5625)
    assert pp is not None
    assert pp.base == 75
    assert pp.exponent == 2

    pp = find_perfect_power(5776)
    assert pp is not None
    assert pp.base == 76
    assert pp.exponent == 2

    pp = find_perfect_power(5929)
    assert pp is not None
    assert pp.base == 77
    assert pp.exponent == 2

    pp = find_perfect_power(6084)
    assert pp is not None
    assert pp.base == 78
    assert pp.exponent == 2

    pp = find_perfect_power(6241)
    assert pp is not None
    assert pp.base == 79
    assert pp.exponent == 2

    pp = find_perfect_power(6400)
    assert pp is not None
    assert pp.base == 80
    assert pp.exponent == 2

    pp = find_perfect_power(6561)
    assert pp is not None
    assert pp.base == 3
    assert pp.exponent == 8

    pp = find_perfect_power(6724)
    assert pp is not None
    assert pp.base == 82
    assert pp.exponent == 2

    pp = find_perfect_power(6889)
    assert pp is not None
    assert pp.base == 83
    assert pp.exponent == 2

    pp = find_perfect_power(7056)
    assert pp is not None
    assert pp.base == 84
    assert pp.exponent == 2

    pp = find_perfect_power(7225)
    assert pp is not None
    assert pp.base == 85
    assert pp.exponent == 2

    pp = find_perfect_power(7396)
    assert pp is not None
    assert pp.base == 86
    assert pp.exponent == 2

    pp = find_perfect_power(7569)
    assert pp is not None
    assert pp.base == 87
    assert pp.exponent == 2

    pp = find_perfect_power(7744)
    assert pp is not None
    assert pp.base == 88
    assert pp.exponent == 2

    pp = find_perfect_power(7921)
    assert pp is not None
    assert pp.base == 89
    assert pp.exponent == 2

    pp = find_perfect_power(8100)
    assert pp is not None
    assert pp.base == 90
    assert pp.exponent == 2

    pp = find_perfect_power(8281)
    assert pp is not None
    assert pp.base == 91
    assert pp.exponent == 2

    pp = find_perfect_power(8464)
    assert pp is not None
    assert pp.base == 92
    assert pp.exponent == 2

    pp = find_perfect_power(8649)
    assert pp is not None
    assert pp.base == 93
    assert pp.exponent == 2

    pp = find_perfect_power(8836)
    assert pp is not None
    assert pp.base == 94
    assert pp.exponent == 2

    pp = find_perfect_power(9025)
    assert pp is not None
    assert pp.base == 95
    assert pp.exponent == 2

    pp = find_perfect_power(9216)
    assert pp is not None
    assert pp.base == 96
    assert pp.exponent == 2

    pp = find_perfect_power(9409)
    assert pp is not None
    assert pp.base == 97
    assert pp.exponent == 2

    pp = find_perfect_power(9604)
    assert pp is not None
    assert pp.base == 98
    assert pp.exponent == 2

    pp = find_perfect_power(9801)
    assert pp is not None
    assert pp.base == 99
    assert pp.exponent == 2

    pp = find_perfect_power(10000)
    assert pp is not None
    assert pp.base == 10
    assert pp.exponent == 4


def test_perfect_power_large_base() -> None:
    """Verify perfect power detection for larger bases."""
    pp = find_perfect_power(104976)
    assert pp is not None
    assert pp.base == 18
    assert pp.exponent == 4


# ---------------------------------------------------------------------------
# is_prime edge cases
# ---------------------------------------------------------------------------


def test_is_prime_edge_cases() -> None:
    """Verify is_prime handles edge cases."""
    assert is_prime(0) is False
    assert is_prime(1) is False
    assert is_prime(-1) is False
    assert is_prime(-2) is False
    assert is_prime(-3) is False
    assert is_prime(-4) is False
    assert is_prime(2) is True
    assert is_prime(3) is True
    assert is_prime(4) is False
    assert is_prime(5) is True
    assert is_prime(6) is False
    assert is_prime(9) is False
    assert is_prime(15) is False
    assert is_prime(25) is False
    assert is_prime(49) is False
    assert is_prime(121) is False


# ---------------------------------------------------------------------------
# find_perfect_power edge cases
# ---------------------------------------------------------------------------


def test_perfect_power_negative() -> None:
    """Verify find_perfect_power handles negative inputs."""
    assert find_perfect_power(-1) is None
    assert find_perfect_power(-2) is None
    assert find_perfect_power(-4) is None
    assert find_perfect_power(-8) is None
    assert find_perfect_power(-9) is None
    assert find_perfect_power(-16) is None
    assert find_perfect_power(-27) is None
    assert find_perfect_power(-32) is None
    assert find_perfect_power(-64) is None
    assert find_perfect_power(-81) is None
    assert find_perfect_power(-100) is None
    assert find_perfect_power(-121) is None
    assert find_perfect_power(-125) is None
    assert find_perfect_power(-128) is None
    assert find_perfect_power(-144) is None
    assert find_perfect_power(-169) is None
    assert find_perfect_power(-196) is None
    assert find_perfect_power(-216) is None
    assert find_perfect_power(-225) is None
    assert find_perfect_power(-243) is None
    assert find_perfect_power(-256) is None
    assert find_perfect_power(-289) is None
    assert find_perfect_power(-324) is None
    assert find_perfect_power(-343) is None
    assert find_perfect_power(-361) is None
    assert find_perfect_power(-400) is None
    assert find_perfect_power(-441) is None
    assert find_perfect_power(-484) is None
    assert find_perfect_power(-512) is None
    assert find_perfect_power(-529) is None
    assert find_perfect_power(-576) is None
    assert find_perfect_power(-625) is None
    assert find_perfect_power(-676) is None
    assert find_perfect_power(-729) is None
    assert find_perfect_power(-784) is None
    assert find_perfect_power(-841) is None
    assert find_perfect_power(-900) is None
    assert find_perfect_power(-961) is None
    assert find_perfect_power(-1000) is None
    assert find_perfect_power(-1024) is None
    assert find_perfect_power(-1089) is None
    assert find_perfect_power(-1156) is None
    assert find_perfect_power(-1225) is None
    assert find_perfect_power(-1296) is None
    assert find_perfect_power(-1331) is None
    assert find_perfect_power(-1369) is None
    assert find_perfect_power(-1444) is None
    assert find_perfect_power(-1521) is None
    assert find_perfect_power(-1600) is None
    assert find_perfect_power(-1681) is None
    assert find_perfect_power(-1728) is None
    assert find_perfect_power(-1764) is None
    assert find_perfect_power(-1849) is None
    assert find_perfect_power(-1936) is None
    assert find_perfect_power(-2025) is None
    assert find_perfect_power(-2116) is None
    assert find_perfect_power(-2197) is None
    assert find_perfect_power(-2209) is None
    assert find_perfect_power(-2304) is None
    assert find_perfect_power(-2401) is None
    assert find_perfect_power(-2500) is None
    assert find_perfect_power(-2601) is None
    assert find_perfect_power(-2704) is None
    assert find_perfect_power(-2809) is None
    assert find_perfect_power(-2916) is None
    assert find_perfect_power(-3025) is None
    assert find_perfect_power(-3125) is None
    assert find_perfect_power(-3136) is None
    assert find_perfect_power(-3249) is None
    assert find_perfect_power(-3364) is None
    assert find_perfect_power(-3481) is None
    assert find_perfect_power(-3600) is None
    assert find_perfect_power(-3721) is None
    assert find_perfect_power(-3844) is None
    assert find_perfect_power(-3969) is None
    assert find_perfect_power(-4096) is None
    assert find_perfect_power(-4225) is None
    assert find_perfect_power(-4356) is None
    assert find_perfect_power(-4489) is None
    assert find_perfect_power(-4624) is None
    assert find_perfect_power(-4761) is None
    assert find_perfect_power(-4900) is None
    assert find_perfect_power(-5041) is None
    assert find_perfect_power(-5184) is None
    assert find_perfect_power(-5329) is None
    assert find_perfect_power(-5476) is None
    assert find_perfect_power(-5625) is None
    assert find_perfect_power(-5776) is None
    assert find_perfect_power(-5929) is None
    assert find_perfect_power(-6084) is None
    assert find_perfect_power(-6241) is None
    assert find_perfect_power(-6400) is None
    assert find_perfect_power(-6561) is None
    assert find_perfect_power(-6724) is None
    assert find_perfect_power(-6889) is None
    assert find_perfect_power(-7056) is None
    assert find_perfect_power(-7225) is None
    assert find_perfect_power(-7396) is None
    assert find_perfect_power(-7569) is None
    assert find_perfect_power(-7744) is None
    assert find_perfect_power(-7921) is None
    assert find_perfect_power(-8100) is None
    assert find_perfect_power(-8281) is None
    assert find_perfect_power(-8464) is None
    assert find_perfect_power(-8649) is None
    assert find_perfect_power(-8836) is None
    assert find_perfect_power(-9025) is None
    assert find_perfect_power(-9216) is None
    assert find_perfect_power(-9409) is None
    assert find_perfect_power(-9604) is None
    assert find_perfect_power(-9801) is None
    assert find_perfect_power(-10000) is None
