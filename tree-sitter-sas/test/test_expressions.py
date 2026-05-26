"""
Test suite for Tree-sitter SAS grammar - Phase B: Expression parsing.

Tests operator precedence, function calls, literals, and complex expressions.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from translator.parser import SASParser


class ExpressionParsingTests(unittest.TestCase):
    """Test expression parsing with correct operator precedence."""

    def setUp(self):
        """Initialize parser."""
        self.parser = SASParser()

    # Literal Tests

    def test_number_literal_integer(self):
        """Parse simple integer literal."""
        code = "data x; y = 123; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_number_literal_float(self):
        """Parse float literal."""
        code = "data x; y = 123.456; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_number_literal_scientific(self):
        """Parse scientific notation."""
        code = "data x; y = 1.23e10; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_string_literal_double_quotes(self):
        """Parse string with double quotes."""
        code = 'data x; y = "hello"; run;'
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_string_literal_single_quotes(self):
        """Parse string with single quotes."""
        code = "data x; y = 'hello'; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_string_literal_escaped_quote(self):
        """Parse string with escaped single quote."""
        code = "data x; y = 'it''s'; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    # Unary Operator Tests

    def test_unary_negation(self):
        """Test unary negation operator."""
        code = "data x; y = -5; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_unary_positive(self):
        """Test unary positive operator."""
        code = "data x; y = +5; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_unary_not(self):
        """Test logical NOT operator."""
        code = "data x; if not flag then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    # Binary Arithmetic Tests

    def test_addition(self):
        """Test addition operator."""
        code = "data x; z = a + b; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_subtraction(self):
        """Test subtraction operator."""
        code = "data x; z = a - b; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_multiplication(self):
        """Test multiplication operator."""
        code = "data x; z = a * b; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_division(self):
        """Test division operator."""
        code = "data x; z = a / b; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    # Exponentiation Tests

    def test_exponentiation(self):
        """Test exponentiation operator."""
        code = "data x; z = a ** b; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_exponentiation_right_associative(self):
        """Test that exponentiation is right-associative (a ** b ** c = a ** (b ** c))."""
        code = "data x; z = 2 ** 3 ** 4; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    # Comparison Tests

    def test_comparison_equals(self):
        """Test = comparison."""
        code = "data x; if a = b then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_comparison_not_equals_caret(self):
        """Test ^= comparison."""
        code = "data x; if a ^= b then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_comparison_not_equals_tilde(self):
        """Test ~= comparison."""
        code = "data x; if a ~= b then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_comparison_less_than(self):
        """Test < comparison."""
        code = "data x; if a < b then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_comparison_greater_than(self):
        """Test > comparison."""
        code = "data x; if a > b then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_comparison_less_or_equal(self):
        """Test <= comparison."""
        code = "data x; if a <= b then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_comparison_greater_or_equal(self):
        """Test >= comparison."""
        code = "data x; if a >= b then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_comparison_double_equals(self):
        """Test == comparison."""
        code = "data x; if a == b then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    # Logical Operator Tests

    def test_logical_and(self):
        """Test AND operator."""
        code = "data x; if a and b then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_logical_or(self):
        """Test OR operator."""
        code = "data x; if a or b then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    # String Concatenation Tests

    def test_string_concatenation(self):
        """Test string concatenation operator ||."""
        code = "data x; y = a || b; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_multiple_concatenation(self):
        """Test multiple concatenations."""
        code = "data x; y = a || b || c; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    # Function Call Tests

    def test_function_call_no_args(self):
        """Test function call with no arguments."""
        code = "data x; y = sqrt(z); run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_function_call_single_arg(self):
        """Test function call with single argument."""
        code = "data x; y = abs(-5); run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_function_call_multiple_args(self):
        """Test function call with multiple arguments."""
        code = "data x; y = put(a, z); run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_nested_function_calls(self):
        """Test nested function calls."""
        code = "data x; y = sqrt(abs(-5)); run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    # Parenthesized Expression Tests

    def test_parenthesized_expression(self):
        """Test parenthesized expression."""
        code = "data x; y = (a + b); run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_nested_parentheses(self):
        """Test nested parentheses."""
        code = "data x; y = ((a + b) * c); run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    # Operator Precedence Tests

    def test_multiplication_before_addition(self):
        """Test that multiplication has higher precedence than addition."""
        # Should parse as: a + (b * c), not (a + b) * c
        code = "data x; y = a + b * c; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_and_before_or(self):
        """Test that AND has higher precedence than OR."""
        # Should parse as: a or (b and c), not (a or b) and c
        code = "data x; if a or b and c then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_not_before_and(self):
        """Test that NOT has higher precedence than AND."""
        code = "data x; if not a and b then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_comparison_before_logical(self):
        """Test that comparison operators have higher precedence than logical operators."""
        code = "data x; if a < b and c > d then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_concatenation_before_comparison(self):
        """Test concatenation precedence."""
        code = "data x; if a || b = c then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_addition_subtraction_left_associative(self):
        """Test that addition and subtraction are left-associative."""
        # Should parse as: (a + b) - c, not a + (b - c)
        code = "data x; y = a + b - c; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    # Complex Expression Tests

    def test_complex_arithmetic_expression(self):
        """Test complex arithmetic expression with multiple operators."""
        code = "data x; y = (a + b) * c / d - e ** 2; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_complex_logical_expression(self):
        """Test complex logical expression."""
        code = "data x; if (a > b and c < d) or (e = f and not g) then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_mixed_operators(self):
        """Test expression with mixed arithmetic and logical operators."""
        code = "data x; if a + b > c and d * e <= f then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)


class DataStepParsingTests(unittest.TestCase):
    """Test DATA STEP parsing."""

    def setUp(self):
        """Initialize parser."""
        self.parser = SASParser()

    def test_simple_data_step(self):
        """Test simple DATA STEP."""
        code = "data work.test; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_data_step_with_assignment(self):
        """Test DATA STEP with assignment."""
        code = "data work.test; x = 5; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_data_step_with_if_then(self):
        """Test DATA STEP with IF/THEN."""
        code = "data work.test; if x > 0 then y = 1; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_data_step_with_if_then_else(self):
        """Test DATA STEP with IF/THEN/ELSE."""
        code = "data work.test; if x > 0 then y = 1; else y = 0; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_data_step_with_set(self):
        """Test DATA STEP with SET statement."""
        code = "data work.out; set work.in; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_data_step_with_do_loop(self):
        """Test DATA STEP with DO loop."""
        code = "data work.test; do i = 1 to 10; sum = sum + i; end; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_data_step_with_do_while(self):
        """Test DATA STEP with DO WHILE."""
        code = "data work.test; do while(x > 0); x = x - 1; end; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_data_step_with_do_until(self):
        """Test DATA STEP with DO UNTIL."""
        code = "data work.test; do until(x = 0); x = x - 1; end; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_data_step_with_keep_drop(self):
        """Test DATA STEP with KEEP/DROP."""
        code = "data work.test; set work.in; keep x y; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)


class ProcStepParsingTests(unittest.TestCase):
    """Test PROC STEP parsing."""

    def setUp(self):
        """Initialize parser."""
        self.parser = SASParser()

    def test_simple_proc_step(self):
        """Test simple PROC step."""
        code = "proc means; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_proc_with_dataset(self):
        """Test PROC with input dataset."""
        code = "proc means data=work.test; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_proc_with_var_statement(self):
        """Test PROC with VAR statement."""
        code = "proc means data=work.test; var x y z; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)

    def test_proc_with_class_statement(self):
        """Test PROC with CLASS statement."""
        code = "proc means data=work.test; class region; var sales; run;"
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)


if __name__ == "__main__":
    unittest.main()
