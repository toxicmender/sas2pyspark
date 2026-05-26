; Keywords
[
  "data"
  "proc"
  "run"
  "quit"
  "set"
  "merge"
  "by"
  "if"
  "then"
  "else"
  "do"
  "end"
  "while"
  "until"
  "to"
  "output"
  "keep"
  "drop"
  "format"
  "length"
  "var"
  "class"
  "where"
  "descending"
  "and"
  "or"
  "not"
  "in"
  "contains"
] @keyword

; Function calls
(function_call name: (identifier) @function)

; Identifiers
(identifier) @variable

; Operators
[
  "="
  "^="
  "<"
  ">"
  "<="
  ">="
  "=="
  "~="
  "+"
  "-"
  "*"
  "/"
  "**"
  "||"
  "."
] @operator

; Literals
(string_literal) @string
(number_literal) @number

; Comments
(comment) @comment
