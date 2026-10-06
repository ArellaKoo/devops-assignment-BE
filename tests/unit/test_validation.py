"""Offline unit tests for SkipQ menu item validation rules (Q4(a)).

These tests run the real model validation code with supplied values only.
No MongoDB connection is attempted: the shared unit fixture sentinel would
fail any accidental socket use, and no fixture here opens a database.
"""

import pytest

from app.errors import DomainError
from app.models.menu_item import MenuItem


def _code(excinfo):
    return excinfo.value.code


class TestPriceRule:
    @pytest.mark.parametrize(
        ("raw", "expected_cents"),
        [
            ("0.01", 1),
            ("1", 100),
            ("6.5", 650),
            ("6.50", 650),
            ("9998.99", 999899),
        ],
    )
    def test_accepts_in_range_price_with_at_most_two_decimals(self, raw, expected_cents):
        """GIVEN a numeric price above zero and below 9999.00 with at most two decimals WHEN it is parsed THEN integer cents are returned."""
        assert MenuItem.parse_price_cents(raw) == expected_cents

    @pytest.mark.parametrize(
        "raw",
        [
            "0",
            "0.00",
            "-0.01",
            "-5",
            "9999.00",
            "10000",
            "9999.99",
            "1.001",
            "12.345",
            "abc",
            "",
            "   ",
            "6.5.1",
            "NaN",
            "Infinity",
            "1e2",
        ],
    )
    def test_refuses_zero_negative_out_of_range_or_malformed_price(self, raw):
        """GIVEN a zero, negative, at-or-above-9999, more-than-two-decimal, or non-numeric price WHEN it is parsed THEN a validation error is raised without cents."""
        with pytest.raises(DomainError) as excinfo:
            MenuItem.parse_price_cents(raw)
        assert _code(excinfo) == "validation_error"


class TestNameRule:
    @pytest.mark.parametrize(
        "raw",
        ["", "   ", "\t", "a" * 81, "a" * 500],
    )
    def test_refuses_blank_or_over_80_character_name(self, raw):
        """GIVEN an item name that is blank or longer than 80 characters WHEN it is validated THEN a validation error names the field limit."""
        with pytest.raises(DomainError) as excinfo:
            MenuItem.validate_name(raw)
        assert _code(excinfo) == "validation_error"

    def test_accepts_single_and_80_character_names_and_trims(self):
        """GIVEN a name of 1 or 80 characters WHEN it is validated THEN the trimmed value is accepted."""
        assert MenuItem.validate_name("a") == "a"
        long_name = "n" * 80
        assert MenuItem.validate_name(long_name) == long_name
        assert MenuItem.validate_name("  Charcoal Rice  ") == "Charcoal Rice"


class TestDescriptionRule:
    def test_refuses_description_over_500_characters(self):
        """GIVEN a description of 501 characters WHEN it is validated THEN a validation error is raised."""
        with pytest.raises(DomainError) as excinfo:
            MenuItem.validate_description("d" * 501)
        assert _code(excinfo) == "validation_error"

    def test_accepts_empty_and_500_character_description(self):
        """GIVEN an empty or 500 character description WHEN it is validated THEN it is accepted."""
        assert MenuItem.validate_description("") == ""
        assert MenuItem.validate_description("d" * 500) == "d" * 500


class TestImageUrlRule:
    @pytest.mark.parametrize(
        "raw",
        [
            "https://cdn.skipq.test/menu/charcoal.jpg",
            "http://127.0.0.1:5001/static/images/skipq-m1.png",
            "https://cdn.skipq.test/menu/photo.jpeg?width=800",
            "https://cdn.skipq.test/menu/photo.PNG",
        ],
    )
    def test_accepts_http_or_https_url_identifying_jpg_jpeg_or_png(self, raw):
        """GIVEN an http or https URL whose path identifies JPG, JPEG or PNG, with optional query string, WHEN it is validated THEN it is accepted."""
        assert MenuItem.validate_image_url(raw) == raw

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "not a url",
            "ftp://cdn.skipq.test/menu/photo.jpg",
            "https://cdn.skipq.test/menu/photo.gif",
            "https://cdn.skipq.test/menu/photo",
            "https://cdn.skipq.test/menu/photo.jpgx",
        ],
    )
    def test_refuses_non_http_or_wrong_format_image_reference(self, raw):
        """GIVEN an empty value, non-http(s) scheme, or a path that does not identify JPG/JPEG/PNG WHEN it is validated THEN a validation error is raised."""
        with pytest.raises(DomainError) as excinfo:
            MenuItem.validate_image_url(raw)
        assert _code(excinfo) == "validation_error"


class TestItemValuesRule:
    def valid_values(self):
        return {
            "name": "Charcoal Chicken Rice",
            "price": "6.50",
            "image_url": "http://127.0.0.1:5001/static/images/skipq-m1.png",
            "description": "Grilled over charcoal.",
        }

    def test_accepts_complete_valid_values_and_returns_cents(self):
        """GIVEN complete valid item values WHEN the item values are validated THEN a normalized mapping with integer cents is returned."""
        cleaned = MenuItem.validate_item_values(self.valid_values())
        assert cleaned["name"] == "Charcoal Chicken Rice"
        assert cleaned["price_cents"] == 650
        assert cleaned["description"] == "Grilled over charcoal."

    def test_defaults_missing_description_and_availability(self):
        """GIVEN valid values without an optional description or availability flag WHEN validated THEN defaults of empty description and available are applied."""
        values = self.valid_values()
        del values["description"]
        cleaned = MenuItem.validate_item_values(values)
        assert cleaned["description"] == ""
        assert cleaned["is_available"] is True

    def test_refuses_missing_required_fields(self):
        """GIVEN values missing the name, price, or image URL WHEN validated THEN a validation error names the missing field."""
        for missing in ("name", "price", "image_url"):
            values = self.valid_values()
            del values[missing]
            with pytest.raises(DomainError) as excinfo:
                MenuItem.validate_item_values(values)
            assert _code(excinfo) == "validation_error"

    def test_refuses_boolean_availability_flag(self):
        """GIVEN a truthy non-boolean availability value WHEN validated THEN a validation error is raised instead of silently accepting it."""
        values = self.valid_values()
        values["is_available"] = "yes"
        with pytest.raises(DomainError) as excinfo:
            MenuItem.validate_item_values(values)
        assert _code(excinfo) == "validation_error"
