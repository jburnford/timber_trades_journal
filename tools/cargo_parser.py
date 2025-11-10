#!/usr/bin/env python3
"""
Parse cargo strings into structured commodity records.
Extracts quantity, unit, commodity, and merchant from cargo field.
"""

import json
import re
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class CargoItem:
    """A single cargo item with quantity, unit, commodity, and merchant."""
    quantity: Optional[str] = None
    unit: Optional[str] = None
    commodity: str = ""
    merchant: Optional[str] = None
    raw_text: str = ""


class CargoParser:
    """Parse cargo strings into structured items."""

    def __init__(self):
        base_dir = Path(__file__).resolve().parent.parent
        units_path = base_dir / "reference_data" / "units.json"
        if not units_path.exists():
            raise FileNotFoundError(f"Unit vocabulary not found at {units_path}")

        with units_path.open("r", encoding="utf-8") as fh:
            units_data = json.load(fh)

        self.abbreviated_units = set(units_data.get("abbreviated", []))
        self.unit_words = set(units_data.get("word_forms", []))
        self.fragments = set(units_data.get("fragments_to_exclude", []))
        self.commodity_whitelist = set(units_data.get("commodity_whitelist", []))

        # Map abbreviated forms (with/without period) to canonical names
        self.unit_normalization = {
            "pcs": "pieces",
            "bdls": "bundles",
            "bgs": "bags",
            "doz": "dozen",
            "lds": "loads",
            "fms": "fathoms",
            "std": "standards",
            "stds": "standards",
            "sq": "square",
            "ft": "feet"
        }

        self.units_to_strip = {
            'pcs', 'pieces', 'piece', 'bdls', 'bundle', 'bundles', 'bgs', 'bags', 'bag',
            'pkg', 'pkgs', 'bx', 'bxs', 'bdl', 'doz', 'lds', 'fms', 'std', 'stds',
            'sq', 'ft', 'bale', 'bales', 'cord', 'cords', 'load', 'loads',
            'package', 'packages', 'fathom', 'fathoms', 'ton', 'tons'
        }
        self.units_to_strip.update({'crts', 'crate', 'crates', 'prs', 'pr', 'dozen', 'dozens', 'dz'})

        abbrev_variants = [rf"{re.escape(u)}\.?" for u in self.abbreviated_units]
        word_variants = [re.escape(u) for u in self.unit_words]

        combined_units = abbrev_variants + word_variants
        self.unit_pattern = f"(?:{'|'.join(combined_units)})" if combined_units else ""

        strip_tokens = sorted(self.units_to_strip, key=len, reverse=True)
        self.unit_prefix_regex = (
            re.compile(r'^(?:' + '|'.join(re.escape(u) for u in strip_tokens) + r')\.?\s+', re.IGNORECASE)
            if strip_tokens else None
        )
        self.merchant_noise_tokens = {
            'with', 'webster', 'co', 'bros', 'brothers', 'son', 'sons',
            'limited', 'ltd', 'company', 'inc', 'order'
        }

        letter_classes = "A-Za-zÀ-ÖØ-öø-ÿ"
        commodity_chars = rf"{letter_classes}\s&\-'"

        self.unified_pattern = re.compile(
            r'(?P<qty>\d[\d,]*)\s+'
            + (
                rf'(?:(?P<unit>{self.unit_pattern})\s+)?'
                if combined_units
                else r'(?:(?P<unit>)\s+)?'
            )
            + rf'(?P<commodity>[{letter_classes}][{commodity_chars}]{{2,60}}?)'
            r'(?=\s*(?:;|—|$)|,\s*(?:(?-i:[A-Z])|\d))',
            re.IGNORECASE
        )

        self.placeholder_merchants = {'order', 'to order', 'in bond', 'nil', 'ditto', ''}
        self.merchant_commodity_words = {
            'deals', 'timber', 'boards', 'battens', 'staves', 'mahogany',
            'cedar', 'oak', 'pine', 'firewood', 'laths', 'planks', 'logs',
            'and', 'bundles', 'pieces'
        }
        self.merchant_suffix_tokens = {
            'co', 'co.', 'sons', 'brothers', 'bros', 'ltd', 'limited', 'company',
            'son', 'sis', 'jr', 'sr'
        }
        self.unit_commodity_fallback = {
            'logs': 'logs',
            'log': 'logs',
            'pieces': 'pieces',
            'piece': 'pieces',
            'pcs': 'pieces',
            'pc': 'pieces',
            'ps': 'pieces',
            'ps.': 'pieces',
            'sticks': 'sticks',
            'stick': 'sticks',
            'bdls': 'bundles',
            'bdl': 'bundles',
            'bundles': 'bundles',
            'pkgs': 'packages',
            'pkg': 'packages',
            'packages': 'packages',
            'lds': 'loads',
            'ld': 'loads',
            'loads': 'loads',
            'prs': 'pairs',
            'pr': 'pairs'
        }
        self.unit_fallback_values = set(self.unit_commodity_fallback.values())

    def normalize_unit(self, unit: Optional[str]) -> Optional[str]:
        if not unit:
            return None
        clean = unit.lower().rstrip('.')
        if clean in self.unit_normalization:
            return self.unit_normalization[clean]
        if clean in self.unit_words:
            return clean
        return clean

    def normalize_merchant(self, merchant: Optional[str]) -> Optional[str]:
        if not merchant:
            return None
        candidate = merchant.strip()
        if not candidate:
            return None

        candidate = re.sub(r'\b(Messrs?|Mrs?|Ms)\.?\s+', '', candidate, flags=re.IGNORECASE)
        candidate = re.sub(r'\s+(Ltd|Limited|Company|Sons?|Brothers?)\s*$', '', candidate, flags=re.IGNORECASE)
        candidate = re.sub(r'\bCo\.\b', 'Co', candidate)
        candidate = candidate.replace('&', 'and')
        candidate = re.sub(r'\s+', ' ', candidate).strip()
        candidate = candidate.rstrip('.,;:')

        if not candidate:
            return None

        lower = candidate.lower()
        if lower in self.placeholder_merchants:
            return None

        # Reject candidates that still carry obvious cargo fragments
        if any(ch.isdigit() for ch in candidate):
            return None
        if any(delim in candidate for delim in {';', ':'}):
            return None

        parts = candidate.split()
        normalized_parts = []
        for part in parts:
            if len(part) <= 2 and part.isupper():
                normalized_parts.append(part)
            elif part.lower() in {'and', 'of', 'the'}:
                normalized_parts.append(part.lower())
            else:
                normalized_parts.append(part.capitalize())

        while normalized_parts and normalized_parts[-1].lower() == 'and':
            normalized_parts.pop()

        normalized = ' '.join(normalized_parts)
        lower_parts = [p.lower() for p in normalized_parts]

        if lower_parts and lower_parts[0] in {'and', 'the'}:
            return None
        if lower_parts and all(word in self.merchant_commodity_words for word in lower_parts):
            return None

        return normalized or None

    def parse_cargo_string(self, cargo: str) -> List[CargoItem]:
        """
        Parse cargo string into structured items.
        """
        if not cargo or len(cargo) < 3:
            return []

        cargo = cargo.strip()
        if not cargo:
            return []

        normalized = cargo.replace('—', ';').replace('–', ';')
        segments = [seg.strip() for seg in normalized.split(';') if seg.strip()]

        items: List[CargoItem] = []

        pending_merchant: Optional[str] = None
        last_items: List[CargoItem] = []

        for segment in segments:
            commodity_text, merchant = self._extract_segment(segment)

            if not commodity_text and merchant:
                targets = last_items if last_items else items[-1:]
                if targets:
                    for item in targets:
                        if not item.merchant:
                            item.merchant = merchant
                else:
                    pending_merchant = merchant
                continue

            if not commodity_text:
                continue

            if not merchant and pending_merchant:
                merchant = pending_merchant
                pending_merchant = None
            elif merchant:
                pending_merchant = None

            components = self._extract_component_items(commodity_text)
            segment_items: List[CargoItem] = []
            for comp in components:
                comp_lower = comp.lower().strip()
                if not comp_lower:
                    continue
                if len(comp_lower) < 3 and comp_lower not in self.commodity_whitelist:
                    continue
                if comp_lower in self.fragments:
                    continue
                if comp_lower in self.unit_words and comp_lower not in self.unit_fallback_values:
                    continue

                item = CargoItem(
                    quantity=None,
                    unit=None,
                    commodity=comp_lower,
                    merchant=merchant,
                    raw_text=segment[:120]
                )
                items.append(item)
                segment_items.append(item)

            if pending_merchant and segment_items:
                for item in segment_items:
                    if not item.merchant:
                        item.merchant = pending_merchant
                pending_merchant = None

            last_items = segment_items if segment_items else []

        return items

    def _extract_segment(self, segment: str) -> (str, Optional[str]):
        segment = segment.strip()
        if not segment:
            return '', None

        merchant = None

        hyphen_match = re.search(r'[-–—]\s*([A-Z][A-Za-zÀ-ÖØ-öø-ÿ\s,\.\'&-]+)$', segment)
        if hyphen_match:
            candidate = hyphen_match.group(1).strip()
            potential = self.normalize_merchant(candidate)
            if potential:
                merchant = potential
                segment = segment[:hyphen_match.start()].strip(' ,;')

        if merchant is None:
            comma_match = re.search(r',\s*([A-Z][A-Za-zÀ-ÖØ-öø-ÿ\s,\.\'&-]+)$', segment)
            if comma_match:
                candidate = comma_match.group(1).strip()
                potential = self.normalize_merchant(candidate)
                if potential:
                    leading = segment[:comma_match.start()].strip(' ,;')
                    if leading and not any(ch.isdigit() for ch in leading):
                        merchant = f"{leading} {potential}".strip()
                        segment = ''
                    else:
                        merchant = potential
                        segment = segment[:comma_match.start()].strip(' ,;')

        segment = self._strip_placeholder_suffix(segment)
        return segment, merchant

    def _extract_component_items(self, text: str) -> List[str]:
        if not text:
            return []

        raw_parts: List[str] = []
        start = 0
        matches = list(self.unified_pattern.finditer(text))

        if matches:
            for match in matches:
                span_start, span_end = match.span()
                pre_text = text[start:span_start].strip(' ,;')
                if pre_text:
                    raw_parts.extend(self._split_commodity_components(pre_text))

                commodity = match.group('commodity').strip()
                raw_parts.extend(self._split_commodity_components(commodity))

                start = span_end

            remainder = text[start:].strip(' ,;')
            if remainder:
                raw_parts.extend(self._split_commodity_components(remainder))
        else:
            raw_parts.extend(self._split_commodity_components(text))

        cleaned_components = []
        seen = set()
        for part in raw_parts:
            component = self._clean_component(part)
            if not component:
                continue
            if component in seen:
                continue
            seen.add(component)
            cleaned_components.append(component)

        return cleaned_components

    def _split_commodity_components(self, text: str) -> List[str]:
        if not text:
            return []

        working = text.replace('&', ' and ')
        segments = []
        for chunk in re.split(r'\s*,\s*', working):
            chunk = chunk.strip(' ,;')
            if not chunk:
                continue
            subparts = [p.strip(' ,;') for p in re.split(r'\band\b', chunk) if p.strip()]
            segments.extend(subparts)
        return segments

    def _clean_component(self, text: str) -> Optional[str]:
        if not text:
            return None

        lower = text.lower().replace('&', ' and ')
        lower = re.sub(r'^\d[\d,]*(?:\.\d+)?\s*', '', lower)
        tokens = [tok for tok in re.split(r'\s+', lower) if tok]
        cleaned_tokens = []

        for token in tokens:
            token = token.strip(" ,;:'\".-")
            if not token:
                continue

            base = token.rstrip('.')
            if base in self.placeholder_merchants or base in {'and', 'of', 'the'}:
                continue
            if base in self.merchant_noise_tokens:
                continue
            if base in self.units_to_strip and len(tokens) > 1:
                continue
            if re.fullmatch(r'\d+', base):
                continue
            if base in self.unit_commodity_fallback:
                cleaned_tokens.append(self.unit_commodity_fallback[base])
                continue

            cleaned_tokens.append(base)

        if not cleaned_tokens:
            fallback_tokens = []
            for token in tokens:
                base = token.lower().strip(" ,;:'\".-")
                if not base:
                    continue
                if base in self.unit_commodity_fallback:
                    fallback_tokens.append(self.unit_commodity_fallback[base])
            if fallback_tokens:
                # Preserve insertion order but drop duplicates
                seen = []
                for token in fallback_tokens:
                    if token not in seen:
                        seen.append(token)
                return ' '.join(seen)
            return None

        cleaned = ' '.join(cleaned_tokens).strip()
        if not cleaned or cleaned in self.placeholder_merchants:
            return None
        if cleaned in self.units_to_strip and cleaned not in self.unit_fallback_values:
            return None
        if cleaned in self.merchant_noise_tokens:
            return None
        return cleaned

    def _split_commodity_and_merchant(self, text: str) -> (str, Optional[str]):
        text = re.sub(r'-(?=[A-Z])', ' ', text)
        tokens = text.split()
        if len(tokens) < 2:
            return text, None

        merchant_tokens = []
        for token in reversed(tokens):
            clean = token.strip(",.")
            lower = clean.lower()
            if merchant_tokens and lower in {'and', '&'}:
                merchant_tokens.append(token)
                continue
            is_initial = bool(re.fullmatch(r'[A-Z]\.?', clean))
            is_suffix = lower in self.merchant_suffix_tokens
            has_amp = '&' in token
            is_capitalized = bool(clean) and clean[0].isupper()

            if is_initial or is_suffix or has_amp or is_capitalized:
                merchant_tokens.append(token)
                continue
            break

        if not merchant_tokens:
            return text, None

        merchant_tokens = merchant_tokens[::-1]
        commodity_tokens = tokens[:-len(merchant_tokens)]
        if not commodity_tokens:
            return text, None

        if len(merchant_tokens) == 1:
            clean = merchant_tokens[0].strip(",.")
            if not clean:
                return text, None
            lower = clean.lower()
            if not clean[0].isupper() and lower not in self.merchant_suffix_tokens:
                return text, None

        merchant_text = ' '.join(merchant_tokens).replace('&', 'and')
        commodity_text = ' '.join(commodity_tokens).strip().rstrip(',;')
        return commodity_text, merchant_text

    def _strip_placeholder_suffix(self, text: str) -> str:
        if not text:
            return text
        cleaned = re.sub(r'(?:,\s*)?(?:to\s+)?order\b.*$', '', text, flags=re.IGNORECASE).strip(' ,;')
        return cleaned

    def extract_commodity_types(self, cargo: str) -> List[str]:
        """
        Extract just the commodity types (simplified).
        """
        return [item.commodity for item in self.parse_cargo_string(cargo) if item.commodity]


def main():
    parser = CargoParser()

    test_cases = [
        "—1,300 staves, Nickols & Colven; 41,500 staves, H. & R. Fowler; 9,173 staves, Oppenheimer & Co.",
        "—102 bgs. wood pulp, J. Spicer & Co.; 1,669 planks, J. Neck & Sons; 8,047 boards, G. E. Arnold",
        "—68 logs wood, 6 logs mahogany, 172 logs rosewood, 104 doz. deals, Order.",
        "—115 pcs. timber, Order.",
        "—46,012 boards, 1,238 bdls. laths, Tagart & Co.",
        "—6,303 battens, and boards",
        "—88 bdls., 2,530 pcs., 20,610 squares, 67 planks black walnut, 20 logs maple, 4 bxs., 30 bdls., 100 logs walnut, 270 pcs. whitewood, 18 bdls., Order"
    ]

    print("=" * 80)
    print("CARGO PARSER TEST (Real Data)")
    print("=" * 80)

    for i, cargo in enumerate(test_cases, 1):
        print(f"\n{i}. Input: {cargo}")
        print("-" * 80)
        items = parser.parse_cargo_string(cargo)
        print(f"   Parsed {len(items)} items:")
        for j, item in enumerate(items, 1):
            print(f"   {j}. Qty: {item.quantity or 'N/A':>6}  "
                  f"Unit: {item.unit or 'N/A':<10}  "
                  f"Commodity: {item.commodity:<30}  "
                  f"Merchant: {(item.merchant or 'N/A')[:25]}")


if __name__ == '__main__':
    main()
