// Tree-sitter Grammar for SAS Language
// Phase B: Full expression grammar with operator precedence
// Phase A skeleton + Phase C macro support built on top

module.exports = grammar({
  name: 'sas',

  extras: $ => [
    /\s+/,
    $.comment,
  ],

  // Inline tokens for lexical elements
  inline: $ => [
    $._statement,
    $._data_stmt,
    $._proc_option,
  ],

  word: $ => $.identifier,

  rules: {
    source_file: $ => repeat($._statement),

    // ============ STATEMENTS (Phase A skeleton) ============

    _statement: $ => choice(
      $.data_step,
      $.proc_step,
      $.run_statement,
      $.quit_statement,
      $.raw_statement,
    ),

    // DATA STEP
    data_step: $ => seq(
      'data',
      optional($.dataset_reference),
      optional($.dataset_options),
      ';',
      repeat($._data_stmt),
      optional('run'),
      ';',
    ),

    _data_stmt: $ => choice(
      $.set_statement,
      $.merge_statement,
      $.by_statement,
      $.assignment_statement,
      $.if_statement,
      $.do_loop,
      $.output_statement,
      $.keep_drop_statement,
      $.format_statement,
      $.length_statement,
      $.drop_statement,
      $.keep_statement,
    ),

    // SET and MERGE statements
    set_statement: $ => seq(
      'set',
      commaSep1($.dataset_reference),
      optional($.dataset_options),
      ';',
    ),

    merge_statement: $ => seq(
      'merge',
      commaSep1($.dataset_reference),
      optional($.dataset_options),
      ';',
    ),

    by_statement: $ => seq(
      'by',
      optional('descending'),
      commaSep1($.identifier),
      ';',
    ),

    // Assignment statement: var = expression;
    assignment_statement: $ => seq(
      $.identifier,
      '=',
      $.expression,
      ';',
    ),

    // IF / THEN / ELSE
    if_statement: $ => seq(
      'if',
      $.expression,
      'then',
      $._data_stmt,
      optional(seq('else', $._data_stmt)),
    ),

    // DO loop
    do_loop: $ => seq(
      'do',
      optional($.do_loop_control),
      ';',
      repeat($._data_stmt),
      'end',
      ';',
    ),

    do_loop_control: $ => choice(
      seq($.identifier, '=', $.expression, 'to', $.expression, optional(seq('by', $.expression))),
      seq('while', '(', $.expression, ')'),
      seq('until', '(', $.expression, ')'),
    ),

    output_statement: $ => seq(
      'output',
      optional(commaSep1($.identifier)),
      ';',
    ),

    keep_drop_statement: $ => seq(
      choice('keep', 'drop'),
      commaSep1($.identifier),
      ';',
    ),

    keep_statement: $ => seq(
      'keep',
      commaSep1($.identifier),
      ';',
    ),

    drop_statement: $ => seq(
      'drop',
      commaSep1($.identifier),
      ';',
    ),

    format_statement: $ => seq(
      'format',
      commaSep1($.format_item),
      ';',
    ),

    format_item: $ => seq(
      commaSep1($.identifier),
      $.format_spec,
    ),

    format_spec: $ => /[a-zA-Z_]\w*\d+\.?\d*/,

    length_statement: $ => seq(
      'length',
      commaSep1($.length_item),
      ';',
    ),

    length_item: $ => seq(
      $.identifier,
      optional('$'),
      $.number_literal,
    ),

    // PROC STEP
    proc_step: $ => seq(
      'proc',
      $.identifier,
      optional($.dataset_reference),
      repeat($.proc_option),
      ';',
      repeat($.proc_stmt),
      optional('run'),
      ';',
    ),

    proc_stmt: $ => choice(
      $.var_statement,
      $.class_statement,
      $.by_statement,
      $.where_statement,
      $.output_statement,
    ),

    _proc_option: $ => choice(
      seq($.identifier, '=', $.expression),
      $.identifier,
    ),

    proc_option: $ => $._proc_option,

    var_statement: $ => seq(
      'var',
      commaSep1($.identifier),
      ';',
    ),

    class_statement: $ => seq(
      'class',
      commaSep1($.identifier),
      ';',
    ),

    where_statement: $ => seq(
      'where',
      $.expression,
      ';',
    ),

    run_statement: $ => seq('run', ';'),
    quit_statement: $ => seq('quit', ';'),

    // ============ EXPRESSIONS (Phase B: Operator Precedence) ============
    // Precedence (lowest to highest):
    // 1. OR
    // 2. AND
    // 3. NOT
    // 4. Comparison (=, ^=, <, >, <=, >=, IN, CONTAINS)
    // 5. Concatenation (||)
    // 6. Addition, Subtraction (+, -)
    // 7. Multiplication, Division (*, /)
    // 8. Unary (-, +, NOT)
    // 9. Exponentiation (**)
    // 10. Primary (literals, identifiers, function calls, parentheses)

    expression: $ => $.logical_or_expr,

    logical_or_expr: $ => prec.left(1, seq(
      $.logical_and_expr,
      repeat(seq('or', $.logical_and_expr)),
    )),

    logical_and_expr: $ => prec.left(2, seq(
      $.logical_not_expr,
      repeat(seq('and', $.logical_not_expr)),
    )),

    logical_not_expr: $ => choice(
      prec(3, seq('not', $.logical_not_expr)),
      $.comparison_expr,
    ),

    comparison_expr: $ => prec.left(4, seq(
      $.concatenation_expr,
      repeat(seq(
        choice(
          '=',
          '^=',
          '<',
          '>',
          '<=',
          '>=',
          '==',
          '~=',
          'in',
          'contains',
        ),
        $.concatenation_expr,
      )),
    )),

    concatenation_expr: $ => prec.left(5, seq(
      $.additive_expr,
      repeat(seq('||', $.additive_expr)),
    )),

    additive_expr: $ => prec.left(6, seq(
      $.multiplicative_expr,
      repeat(seq(
        choice('+', '-'),
        $.multiplicative_expr,
      )),
    )),

    multiplicative_expr: $ => prec.left(7, seq(
      $.exponentiation_expr,
      repeat(seq(
        choice('*', '/'),
        $.exponentiation_expr,
      )),
    )),

    exponentiation_expr: $ => prec.right(9, seq(
      $.unary_expr,
      repeat(seq('**', $.unary_expr)),
    )),

    unary_expr: $ => choice(
      prec(8, seq(choice('-', '+', 'not'), $.unary_expr)),
      $.primary_expr,
    ),

    primary_expr: $ => choice(
      $.number_literal,
      $.string_literal,
      $.identifier,
      $.function_call,
      seq('(', $.expression, ')'),
    ),

    // ============ FUNCTION CALLS ============
    function_call: $ => seq(
      $.identifier,
      '(',
      optional(commaSep1($.expression)),
      ')',
    ),

    // ============ DATASET REFERENCES & OPTIONS ============
    dataset_reference: $ => choice(
      seq($.libref, '.', $.identifier),
      $.identifier,
    ),

    libref: $ => /[a-zA-Z_]\w*/,

    dataset_options: $ => seq(
      '(',
      optional(commaSep1($.dataset_option)),
      ')',
    ),

    dataset_option: $ => seq(
      $.identifier,
      optional(seq('=', $.expression)),
    ),

    // ============ LITERALS ============
    identifier: $ => /[a-zA-Z_]\w*/i,

    string_literal: $ => choice(
      /"(?:\\.|[^"\\])*"/,
      /'(?:''|[^'])*'/,
    ),

    number_literal: $ => choice(
      /\d+\.\d+([eE][+-]?\d+)?/,
      /\d+[eE][+-]?\d+/,
      /\d+/,
    ),

    // ============ COMMENTS ============
    comment: $ => choice(
      seq('*', /[^;]*/, ';'),
      seq('/*', /[\s\S]*?/, '*/'),
    ),

    // ============ RAW STATEMENT (catch-all for unparsed constructs) ============
    raw_statement: $ => seq(
      /[a-zA-Z_]\w*/i,
      repeat(/[^;]+/),
      ';',
    ),
  },
});

/**
 * Helper: commaSep1(rule)
 * Matches one or more occurrences of 'rule' separated by commas.
 */
function commaSep1(rule) {
  return seq(rule, repeat(seq(',', rule)));
}
