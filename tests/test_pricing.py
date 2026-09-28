from __future__ import annotations

import dataclasses
import sys
import unittest
from collections.abc import Mapping
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import collect

PLACES = 6
MILLION = 1_000_000
PRICING_SOURCE = 'https://platform.claude.com/docs/en/about-claude/pricing.md'
US_INFERENCE_MULTIPLIER = 1.1
US_INFERENCE_GEO = 'us'
SYNTHETIC_MODEL = '<synthetic>'
UNKNOWN_MODEL = 'gpt-4'
OPUS_5_5 = 'claude-opus-5-5'
OPUS_5 = 'claude-opus-5'
SONNET_5 = 'claude-sonnet-5'
PRICING_FIELDS = ['input', 'output', 'cache_write_5m', 'cache_write_1h', 'cache_read']
FULL_USAGE = {
    'input_tokens': MILLION,
    'output_tokens': MILLION,
    'cache_read_input_tokens': MILLION,
    'cache_creation_input_tokens': 2 * MILLION,
    'cache_creation': {'ephemeral_5m_input_tokens': MILLION, 'ephemeral_1h_input_tokens': MILLION},
}
FAST_USAGE = {**FULL_USAGE, 'speed': 'fast'}
STANDARD_COSTS = (
    (OPUS_5_5, 37.20),
    ('claude-fable-5-1', 92.75),
    ('claude-fable-5', 93.50),
    (OPUS_5, 46.75),
    (SONNET_5, 18.70),
    ('claude-haiku-4-5-20251001', 9.35),
    ('claude-opus-4-1-20250805', 140.25),
    ('claude-sonnet-4-5-20250929', 28.05),
)
FAST_COSTS = (
    (OPUS_5_5, 74.40),
    (OPUS_5, 93.50),
    ('claude-opus-4-8', 93.50),
)
CANONICAL_MODELS = (
    (OPUS_5_5, OPUS_5_5),
    ('claude-opus-5-5[1m]', OPUS_5_5),
    ('claude-haiku-4-5-20251001', 'claude-haiku-4-5'),
    ('claude-sonnet-4-5-20250929[1m]', 'claude-sonnet-4-5'),
    ('claude-opus-4-5-20251101', 'claude-opus-4-5'),
    ('claude-opus-4-20250514', 'claude-opus-4-0'),
    ('claude-sonnet-4-20250514', 'claude-sonnet-4-0'),
    ('claude-opus-4', 'claude-opus-4-0'),
    ('claude-sonnet-4', 'claude-sonnet-4-0'),
    ('claude-3-5-haiku-20241022', 'claude-3-5-haiku'),
    ('claude-mythos-5-1', 'claude-mythos-5-1'),
    (UNKNOWN_MODEL, None),
    (SYNTHETIC_MODEL, None),
)


class PricingTest(unittest.TestCase):
    def assert_same_rates(self, actual: collect.Pricing, expected: collect.Pricing) -> None:
        self.assertIsInstance(actual, collect.Pricing)
        for field in PRICING_FIELDS:
            self.assertAlmostEqual(getattr(actual, field), getattr(expected, field), places=PLACES, msg=field)

    def assert_pricing_table(
        self,
        actual: Mapping[str, collect.Pricing],
        expected: Mapping[tuple[str, ...], collect.Pricing],
    ) -> None:
        self.assertEqual(sorted(actual), sorted(model for models in expected for model in models))
        for models, pricing in expected.items():
            for model in models:
                with self.subTest(model=model):
                    self.assert_same_rates(actual[model], pricing)

    def test_pricing_is_a_frozen_dataclass(self) -> None:
        self.assertEqual([field.name for field in dataclasses.fields(collect.Pricing)], PRICING_FIELDS)
        pricing = collect.Pricing(input=1, output=2, cache_write_5m=3, cache_write_1h=4, cache_read=5)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            pricing.input = 6

    def test_pricing_is_the_only_class(self) -> None:
        classes = [
            name for name, value in vars(collect).items()
            if isinstance(value, type) and value.__module__ == collect.__name__
        ]
        self.assertEqual(classes, ['Pricing'])

    def test_pricing_constants(self) -> None:
        self.assertEqual(collect.PRICING_SOURCE, PRICING_SOURCE)
        self.assertEqual(collect.US_INFERENCE_MULTIPLIER, US_INFERENCE_MULTIPLIER)
        self.assertEqual(collect.SYNTHETIC_MODEL, SYNTHETIC_MODEL)

    def test_model_pricing_matches_the_pricing_page(self) -> None:
        self.assert_pricing_table(collect.MODEL_PRICING, {
            ('claude-fable-5-1', 'claude-mythos-5-1'): collect.Pricing(
                input=10, output=50, cache_write_5m=12.5, cache_write_1h=20, cache_read=0.25,
            ),
            ('claude-fable-5', 'claude-mythos-5'): collect.Pricing(
                input=10, output=50, cache_write_5m=12.5, cache_write_1h=20, cache_read=1,
            ),
            (OPUS_5_5,): collect.Pricing(
                input=4, output=20, cache_write_5m=5, cache_write_1h=8, cache_read=0.2,
            ),
            (OPUS_5, 'claude-opus-4-8', 'claude-opus-4-7', 'claude-opus-4-6', 'claude-opus-4-5'): collect.Pricing(
                input=5, output=25, cache_write_5m=6.25, cache_write_1h=10, cache_read=0.5,
            ),
            ('claude-opus-4-1', 'claude-opus-4-0'): collect.Pricing(
                input=15, output=75, cache_write_5m=18.75, cache_write_1h=30, cache_read=1.5,
            ),
            (SONNET_5,): collect.Pricing(
                input=2, output=10, cache_write_5m=2.5, cache_write_1h=4, cache_read=0.2,
            ),
            ('claude-sonnet-4-6', 'claude-sonnet-4-5', 'claude-sonnet-4-0'): collect.Pricing(
                input=3, output=15, cache_write_5m=3.75, cache_write_1h=6, cache_read=0.3,
            ),
            ('claude-haiku-4-5',): collect.Pricing(
                input=1, output=5, cache_write_5m=1.25, cache_write_1h=2, cache_read=0.1,
            ),
            ('claude-3-5-haiku',): collect.Pricing(
                input=0.8, output=4, cache_write_5m=1, cache_write_1h=1.6, cache_read=0.08,
            ),
        })

    def test_fast_mode_pricing_matches_the_pricing_page(self) -> None:
        self.assert_pricing_table(collect.FAST_MODE_PRICING, {
            (OPUS_5_5,): collect.Pricing(
                input=8, output=40, cache_write_5m=10, cache_write_1h=16, cache_read=0.4,
            ),
            (OPUS_5, 'claude-opus-4-8'): collect.Pricing(
                input=10, output=50, cache_write_5m=12.5, cache_write_1h=20, cache_read=1,
            ),
        })

    def test_canonical_model(self) -> None:
        for model, canonical in CANONICAL_MODELS:
            with self.subTest(model=model):
                self.assertEqual(collect.canonical_model(model), canonical)

    def test_standard_rates(self) -> None:
        for model, cost in STANDARD_COSTS:
            with self.subTest(model=model):
                self.assertAlmostEqual(collect.estimate_cost(model, FULL_USAGE), cost, places=PLACES)

    def test_fast_mode_rates(self) -> None:
        for model, cost in FAST_COSTS:
            with self.subTest(model=model):
                self.assertAlmostEqual(collect.estimate_cost(model, FAST_USAGE), cost, places=PLACES)

    def test_fast_mode_without_fast_rates_uses_standard_rates(self) -> None:
        self.assertAlmostEqual(collect.estimate_cost(SONNET_5, FAST_USAGE), 18.70, places=PLACES)

    def test_context_window_suffix_uses_base_rates(self) -> None:
        cost = collect.estimate_cost('claude-opus-5-5[1m]', FULL_USAGE)
        self.assertAlmostEqual(cost, collect.estimate_cost(OPUS_5_5, FULL_USAGE), places=PLACES)
        self.assertAlmostEqual(cost, 37.20, places=PLACES)

    def test_cache_writes_without_breakdown_use_five_minute_rate(self) -> None:
        usage = {'cache_creation_input_tokens': MILLION}
        self.assertAlmostEqual(collect.estimate_cost(OPUS_5, usage), 6.25, places=PLACES)

    def test_us_inference_costs_ten_percent_more(self) -> None:
        usage = {'input_tokens': MILLION, 'inference_geo': US_INFERENCE_GEO}
        self.assertAlmostEqual(collect.estimate_cost(OPUS_5, usage), 5.50, places=PLACES)
        fast_usage = {**FAST_USAGE, 'inference_geo': US_INFERENCE_GEO}
        self.assertAlmostEqual(collect.estimate_cost(OPUS_5_5, fast_usage), 81.84, places=PLACES)

    def test_unknown_model_is_unpriced(self) -> None:
        self.assertIsNone(collect.estimate_cost(UNKNOWN_MODEL, FULL_USAGE))

    def test_synthetic_model_is_free(self) -> None:
        self.assertEqual(collect.estimate_cost(SYNTHETIC_MODEL, FULL_USAGE), 0.0)


if __name__ == '__main__':
    unittest.main()
