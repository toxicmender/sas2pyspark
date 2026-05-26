; Variable definitions in assignment statements
(assignment_statement
  (identifier) @definition.var)

; Function parameters (when we support custom functions)
(function_call
  (identifier) @function)

; Scope tracking for DO loops
(do_loop
  (do_loop_control
    (identifier) @definition.var))

; Variable references
(identifier) @reference
