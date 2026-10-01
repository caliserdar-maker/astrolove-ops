#!/usr/bin/env python3
"""WP bakir kilidi (Serdar 1 Eki WP PASS): kilitli kaynak ve parametreler wp_kilit.json ile ayni olmali."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_kilit                                                   # noqa: E402


def test_kilit():
    f = wp_kilit.fark()
    assert not f, f'kilitli WP bakir kodu degismis: {f}'


if __name__ == '__main__':
    test_kilit(); print('PASS test_kilit')
