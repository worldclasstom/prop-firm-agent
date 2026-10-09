import copy
import unittest
from unittest.mock import patch

from propfirm.backtest import challenge_windows, simulate
from propfirm.config import validate_markets
from propfirm.data import DAY
from test_execution import MARKET


def history(first, count):
    return [{'t': i * DAY, 'o': '100', 'h': '101', 'l': '99', 'c': '100', 'v': '10'}
            for i in range(first, first + count)]


class CalendarWindowTests(unittest.TestCase):
    def test_new_listing_does_not_erase_older_windows(self):
        histories = {'old': history(0, 400), 'new': history(335, 65)}
        result = challenge_windows(histories, {a: MARKET for a in histories})
        self.assertEqual(result['window_denominator'], 3)
        self.assertEqual(result['partial_tail_days'], 70)
        for window in result['challenge_windows']:
            self.assertEqual(window['modeled_days'], 90)
            self.assertEqual(set(window['market_coverage']), {'old', 'new'})
            self.assertIsNone(window['market_coverage']['new']['eligible_from_epoch_ms'])

    def test_calendar_alignment_and_late_market_warmup(self):
        histories = {'old': history(0, 150), 'late': history(30, 120)}
        result = challenge_windows(histories, {a: MARKET for a in histories})
        window = result['challenge_windows'][0]
        self.assertEqual((window['start_epoch_ms'], window['end_exclusive_epoch_ms']), (60 * DAY, 150 * DAY))
        self.assertEqual(window['market_coverage']['late']['eligible_from_epoch_ms'], 90 * DAY)
        self.assertEqual(window['market_coverage']['late']['evaluation_bars'], 60)

    def test_partial_window_is_not_counted(self):
        for count, expected, tail in ((149, 0, 89), (150, 1, 0), (239, 1, 89), (240, 2, 0)):
            with self.subTest(count=count):
                result = challenge_windows({'a': history(0, count)}, {'a': MARKET})
                self.assertEqual(result['window_denominator'], expected)
                self.assertEqual(result['partial_tail_days'], tail)
        self.assertEqual(challenge_windows({'a': history(0, 60)}, {'a': MARKET})['window_denominator'], 0)

    def test_missing_market_dates_flagged_without_realigning_rows(self):
        histories = {'full': history(0, 150), 'gap': history(0, 150)}
        histories['gap'].pop(100)
        result = challenge_windows(histories, {a: MARKET for a in histories})
        window = result['challenge_windows'][0]
        self.assertEqual(window['market_coverage']['gap']['missing_eligible_days'], 1)
        self.assertEqual(window['failure_or_uncertainty'], 'incomplete_market_history')
        self.assertEqual(result['flagged_windows'], 1)

    def test_later_window_keeps_atr_history_and_excludes_future(self):
        rows = history(0, 250)
        before = copy.deepcopy(rows)
        with patch('propfirm.backtest.simulate', wraps=simulate) as run:
            challenge_windows({'a': rows}, {'a': MARKET})
        args, kwargs = run.call_args_list[1]
        self.assertEqual(kwargs['start_at'], 150 * DAY)
        self.assertEqual(args[0]['a'][0]['t'], 0)
        self.assertEqual(args[0]['a'][-1]['t'], 239 * DAY)
        self.assertEqual(rows, before)

    def test_empty_watchlist_is_distinct_from_duplicates(self):
        with self.assertRaisesRegex(ValueError, 'No verified markets configured'):
            validate_markets({'markets': []})
        with self.assertRaisesRegex(ValueError, 'Duplicate market identifiers'):
            validate_markets({'markets': [MARKET, MARKET]})


if __name__ == '__main__':
    unittest.main()
