from __future__ import annotations

import re
from dataclasses import dataclass

from .ast import (
    AssignmentStatement,
    BinaryOp,
    ByStatement,
    DataStep,
    DeleteStatement,
    DropStatement,
    ElseStatement,
    Expression,
    FunctionCall,
    Identifier,
    IfStatement,
    KeepStatement,
    MergeStatement,
    NumberLiteral,
    OutputStatement,
    ProcStep,
    RawExpression,
    RawStatement,
    SetStatement,
    SourceFile,
    Statement,
    StringLiteral,
    UnaryOp,
)
from .diagnostics import Diagnostic, DiagnosticLevel


@dataclass
class ParseResult:
    ast: SourceFile
    diagnostics: list[Diagnostic]


@dataclass(frozen=True)
class Token:
    type: str
    value: str


def parse_source(source: str) -> ParseResult:
    diagnostics: list[Diagnostic] = []
    statements = split_statements(source)
    ast_statements: list[Statement] = []
    index = 0

    while index < len(statements):
        statement = statements[index].strip()
        if not statement:
            index += 1
            continue
        lowered = statement.lower()
        if lowered.startswith("data "):
            data_step, consumed = parse_data_step(statements, index, diagnostics)
            ast_statements.append(data_step)
            index += consumed
            continue
        if lowered.startswith("proc "):
            proc_step, consumed = parse_proc_step(statements, index, diagnostics)
            ast_statements.append(proc_step)
            index += consumed
            continue
        ast_statements.append(RawStatement(statement))
        diagnostics.append(
            Diagnostic(
                DiagnosticLevel.WARNING,
                f"Unsupported top-level statement: {statement}",
            )
        )
        index += 1

    return ParseResult(ast=SourceFile(ast_statements), diagnostics=diagnostics)


def parse_proc_step(
    statements: list[str],
    start_index: int,
    diagnostics: list[Diagnostic],
) -> tuple[ProcStep, int]:
    header = statements[start_index].strip()
    match = re.match(r"(?is)^proc\s+([a-z_][\w]*)\s*(.*)$", header)
    if not match:
        diagnostics.append(
            Diagnostic(DiagnosticLevel.ERROR, f"Invalid PROC statement: {header}")
        )
        return ProcStep("unknown", None, []), 1

    name = match.group(1)
    options = match.group(2).strip() or None
    proc_statements: list[Statement] = []

    index = start_index + 1
    while index < len(statements):
        statement = statements[index].strip()
        if not statement:
            index += 1
            continue
        if statement.lower() in {"run", "quit"}:
            index += 1
            break
        proc_statements.append(RawStatement(statement))
        index += 1

    consumed_total = index - start_index
    return ProcStep(
        name=name, options=options, statements=proc_statements
    ), consumed_total


def parse_data_step(
    statements: list[str],
    start_index: int,
    diagnostics: list[Diagnostic],
) -> tuple[DataStep, int]:
    header = statements[start_index].strip()
    outputs = parse_data_outputs(header, diagnostics)
    data_statements: list[Statement] = []

    index = start_index + 1
    while index < len(statements):
        statement = statements[index].strip()
        if not statement:
            index += 1
            continue
        if statement.lower() in {"run", "quit"}:
            index += 1
            break
        parsed, consumed = parse_data_statement(statements, index, diagnostics)
        if isinstance(parsed, ElseStatement):
            if not attach_else_clause(data_statements, parsed, diagnostics):
                diagnostics.append(
                    Diagnostic(
                        DiagnosticLevel.ERROR,
                        f"ELSE without matching IF: {statement}",
                    )
                )
            index += consumed
            continue
        if parsed is not None:
            data_statements.append(parsed)
        index += consumed

    consumed_total = index - start_index
    return DataStep(outputs=outputs, statements=data_statements), consumed_total


def attach_else_clause(
    statements: list[Statement],
    else_stmt: ElseStatement,
    diagnostics: list[Diagnostic],
) -> bool:
    if not statements:
        diagnostics.append(
            Diagnostic(DiagnosticLevel.ERROR, "ELSE without preceding IF")
        )
        return False
    last = statements[-1]
    if not isinstance(last, IfStatement) or last.alternative is not None:
        diagnostics.append(
            Diagnostic(DiagnosticLevel.ERROR, "ELSE without matching IF")
        )
        return False
    if else_stmt.statement is None:
        diagnostics.append(
            Diagnostic(DiagnosticLevel.ERROR, "ELSE clause is missing a statement")
        )
        return False
    statements[-1] = IfStatement(
        condition=last.condition,
        consequence=last.consequence,
        alternative=else_stmt.statement,
    )
    return True


def parse_data_outputs(header: str, diagnostics: list[Diagnostic]) -> list[str]:
    match = re.match(r"(?is)^data\s+(.*)$", header)
    if not match:
        diagnostics.append(
            Diagnostic(DiagnosticLevel.ERROR, f"Invalid DATA statement: {header}")
        )
        return []
    output_text = match.group(1).strip()
    outputs = parse_dataset_list(output_text)
    if not outputs:
        diagnostics.append(
            Diagnostic(DiagnosticLevel.ERROR, f"Missing DATA output dataset: {header}")
        )
    return outputs


def parse_data_statement(
    statements: list[str],
    index: int,
    diagnostics: list[Diagnostic],
) -> tuple[Statement | None, int]:
    statement = statements[index].strip()
    lowered = statement.lower()

    if lowered.startswith("set "):
        datasets = parse_dataset_list(statement[4:])
        return SetStatement(datasets), 1

    if lowered.startswith("merge "):
        datasets = parse_dataset_list(statement[6:])
        return MergeStatement(datasets), 1

    if lowered.startswith("by "):
        columns = parse_by_list(statement[3:])
        return ByStatement(columns), 1

    if lowered.startswith("keep "):
        columns = parse_name_list(statement[5:])
        return KeepStatement(columns), 1

    if lowered.startswith("drop "):
        columns = parse_name_list(statement[5:])
        return DropStatement(columns), 1

    if lowered.startswith("output"):
        output = parse_output_statement(statement, diagnostics)
        return output, 1

    if lowered.startswith("delete"):
        return DeleteStatement(), 1

    if lowered.startswith("if "):
        next_statement = None
        if index + 1 < len(statements):
            next_statement = statements[index + 1].strip()
        if_stmt, consumed = parse_if_statement(statement, next_statement, diagnostics)
        return if_stmt, consumed

    if lowered.startswith("else"):
        inner = re.sub(r"(?is)^else\b", "", statement).strip()
        inner_stmt = parse_inline_statement(inner, diagnostics)
        return ElseStatement(inner_stmt), 1

    assignment = parse_assignment(statement, diagnostics)
    if assignment is not None:
        return assignment, 1

    diagnostics.append(
        Diagnostic(
            DiagnosticLevel.WARNING, f"Unsupported DATA step statement: {statement}"
        )
    )
    return RawStatement(statement), 1


def parse_if_statement(
    statement: str,
    next_statement: str | None,
    diagnostics: list[Diagnostic],
) -> tuple[IfStatement, int]:
    match = re.match(r"(?is)^if\s+(.*?)\s+then\s+(.*)$", statement)
    if not match:
        diagnostics.append(
            Diagnostic(DiagnosticLevel.ERROR, f"Invalid IF statement: {statement}")
        )
        condition = RawExpression("invalid")
        return IfStatement(condition, RawStatement(""), None), 1

    condition_text = match.group(1).strip()
    remainder = match.group(2).strip()

    then_text, else_text = split_else_clause(remainder)
    consumed = 1

    if else_text is None and next_statement is not None:
        if re.match(r"(?is)^else\b", next_statement):
            else_text = re.sub(r"(?is)^else\b", "", next_statement).strip()
            consumed = 2

    condition_expr = parse_expression(condition_text, diagnostics)
    then_stmt = parse_inline_statement(then_text, diagnostics)
    if then_stmt is None:
        diagnostics.append(
            Diagnostic(
                DiagnosticLevel.ERROR, f"Unsupported IF consequence: {then_text}"
            )
        )
        then_stmt = RawStatement(then_text)

    alternative = None
    if else_text is not None:
        else_stmt = parse_inline_statement(else_text, diagnostics)
        if else_stmt is None:
            diagnostics.append(
                Diagnostic(
                    DiagnosticLevel.ERROR, f"Unsupported IF alternative: {else_text}"
                )
            )
        else:
            alternative = else_stmt

    return IfStatement(condition_expr, then_stmt, alternative), consumed


def parse_inline_statement(
    text: str, diagnostics: list[Diagnostic]
) -> Statement | None:
    if not text:
        return None
    assignment = parse_assignment(text, diagnostics)
    if assignment is not None:
        return assignment
    if text.lower().startswith("output"):
        return parse_output_statement(text, diagnostics)
    if text.lower().startswith("delete"):
        return DeleteStatement()
    diagnostics.append(
        Diagnostic(DiagnosticLevel.WARNING, f"Unsupported inline statement: {text}")
    )
    return RawStatement(text)


def parse_output_statement(text: str, diagnostics: list[Diagnostic]) -> OutputStatement:
    match = re.match(r"(?is)^output\b(.*)$", text)
    if not match:
        diagnostics.append(
            Diagnostic(DiagnosticLevel.ERROR, f"Invalid OUTPUT statement: {text}")
        )
        return OutputStatement(None)
    remainder = match.group(1).strip()
    if not remainder:
        return OutputStatement(None)
    datasets = parse_dataset_list(remainder)
    if len(datasets) > 1:
        diagnostics.append(
            Diagnostic(
                DiagnosticLevel.WARNING,
                "Multiple OUTPUT targets found; only the first is captured",
            )
        )
    return OutputStatement(datasets[0] if datasets else None)


def split_else_clause(text: str) -> tuple[str, str | None]:
    match = re.search(r"(?is)\belse\b", text)
    if not match:
        return text.strip(), None
    then_text = text[: match.start()].strip()
    else_text = text[match.end() :].strip()
    return then_text, else_text


def parse_dataset_list(text: str) -> list[str]:
    tokens = [token for token in re.split(r"[\s,]+", text.strip()) if token]
    datasets = [strip_dataset_options(token) for token in tokens]
    return [dataset for dataset in datasets if dataset]


def strip_dataset_options(token: str) -> str:
    return re.split(r"\(", token, maxsplit=1)[0].strip()


def parse_name_list(text: str) -> list[str]:
    return [token for token in re.split(r"[\s,]+", text.strip()) if token]


def parse_by_list(text: str) -> list[str]:
    tokens = parse_name_list(text)
    skip = {"descending", "notsorted"}
    return [token for token in tokens if token.lower() not in skip]


def parse_assignment(
    statement: str, diagnostics: list[Diagnostic]
) -> AssignmentStatement | None:
    match = re.match(r"(?is)^([a-z_][\w\.]*)\s*=\s*(.+)$", statement)
    if not match:
        return None
    target = match.group(1)
    expression_text = match.group(2).strip()
    expression = parse_expression(expression_text, diagnostics)
    return AssignmentStatement(target, expression)


def parse_expression(text: str, diagnostics: list[Diagnostic]) -> Expression:
    if not text:
        diagnostics.append(Diagnostic(DiagnosticLevel.ERROR, "Empty expression"))
        return RawExpression("")
    try:
        tokens = tokenize_expression(text)
        parser = ExpressionParser(tokens)
        expr = parser.parse()
        if parser.peek().type != "EOF":
            diagnostics.append(
                Diagnostic(
                    DiagnosticLevel.WARNING,
                    f"Unparsed tokens in expression: {text}",
                )
            )
            return RawExpression(text.strip())
        return expr
    except ValueError as exc:
        diagnostics.append(Diagnostic(DiagnosticLevel.ERROR, str(exc)))
        return RawExpression(text.strip())


def split_statements(source: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    in_string = False
    index = 0

    while index < len(source):
        char = source[index]
        if char == "'":
            if in_string and index + 1 < len(source) and source[index + 1] == "'":
                buffer.append("''")
                index += 2
                continue
            in_string = not in_string
            buffer.append(char)
            index += 1
            continue
        if char == ";" and not in_string:
            statement = "".join(buffer).strip()
            statements.append(statement)
            buffer = []
            index += 1
            continue
        buffer.append(char)
        index += 1

    trailing = "".join(buffer).strip()
    if trailing:
        statements.append(trailing)
    return statements


def tokenize_expression(text: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0

    while index < len(text):
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char == "'":
            value, index = read_string(text, index)
            tokens.append(Token("STRING", value))
            continue
        if char.isdigit():
            value, index = read_number(text, index)
            tokens.append(Token("NUMBER", value))
            continue
        if char.isalpha() or char == "_":
            value, index = read_identifier(text, index)
            lower_value = value.lower()
            if lower_value in {"and", "or", "not"}:
                tokens.append(Token("OP", lower_value))
            else:
                tokens.append(Token("IDENT", value))
            continue
        if char in {"(", ")", ","}:
            tokens.append(Token(char, char))
            index += 1
            continue

        op, index = read_operator(text, index)
        tokens.append(Token("OP", op))

    tokens.append(Token("EOF", ""))
    return tokens


def read_string(text: str, start: int) -> tuple[str, int]:
    index = start + 1
    value_chars: list[str] = []
    while index < len(text):
        char = text[index]
        if char == "'":
            if index + 1 < len(text) and text[index + 1] == "'":
                value_chars.append("'")
                index += 2
                continue
            return "".join(value_chars), index + 1
        value_chars.append(char)
        index += 1
    raise ValueError("Unterminated string literal")


def read_number(text: str, start: int) -> tuple[str, int]:
    index = start
    while index < len(text) and (text[index].isdigit() or text[index] == "."):
        index += 1
    return text[start:index], index


def read_identifier(text: str, start: int) -> tuple[str, int]:
    index = start
    while index < len(text) and (text[index].isalnum() or text[index] in {"_", "."}):
        index += 1
    return text[start:index], index


def read_operator(text: str, start: int) -> tuple[str, int]:
    operators = [">=", "<=", "!=", "<>", "~=", "^=", "=="]
    for op in operators:
        if text.startswith(op, start):
            return op, start + len(op)
    if text[start] in {">", "<", "=", "+", "-", "*", "/"}:
        return text[start], start + 1
    raise ValueError(f"Unexpected character in expression: {text[start]}")


class ExpressionParser:
    def __init__(self, tokens: list[Token]):
        self.tokens: list[Token] = tokens
        self.position: int = 0

    def peek(self) -> Token:
        return self.tokens[self.position]

    def advance(self) -> Token:
        current = self.tokens[self.position]
        self.position += 1
        return current

    def parse(self) -> Expression:
        return self.parse_expression(0)

    def parse_expression(self, min_bp: int) -> Expression:
        token = self.advance()
        left = self.nud(token)
        while True:
            token = self.peek()
            if token.type != "OP":
                break
            lbp, rbp = infix_binding_power(token.value)
            if lbp < min_bp:
                break
            op = self.advance().value
            right = self.parse_expression(rbp)
            left = BinaryOp(left, op, right)
        return left

    def nud(self, token: Token) -> Expression:
        if token.type == "IDENT":
            if self.peek().type == "(":
                _ = self.advance()
                args = self.parse_arguments()
                return FunctionCall(token.value, args)
            return Identifier(token.value)
        if token.type == "NUMBER":
            if "." in token.value:
                return NumberLiteral(float(token.value))
            return NumberLiteral(int(token.value))
        if token.type == "STRING":
            return StringLiteral(token.value)
        if token.type == "OP" and token.value in {"-", "+", "not"}:
            operand = self.parse_expression(100)
            return UnaryOp(token.value, operand)
        if token.type == "(":
            expr = self.parse_expression(0)
            if self.peek().type != ")":
                raise ValueError("Unbalanced parentheses in expression")
            _ = self.advance()
            return expr
        raise ValueError(f"Unexpected token in expression: {token}")

    def parse_arguments(self) -> list[Expression]:
        args: list[Expression] = []
        if self.peek().type == ")":
            _ = self.advance()
            return args
        while True:
            args.append(self.parse_expression(0))
            if self.peek().type == ",":
                _ = self.advance()
                continue
            if self.peek().type == ")":
                _ = self.advance()
                break
            raise ValueError("Expected ',' or ')' in function arguments")
        return args


def infix_binding_power(op: str) -> tuple[int, int]:
    op_lower = op.lower()
    if op_lower == "or":
        return 1, 2
    if op_lower == "and":
        return 3, 4
    if op_lower in {"=", "==", "!=", "<>", "~=", "^=", ">", "<", ">=", "<="}:
        return 5, 6
    if op_lower in {"+", "-"}:
        return 7, 8
    if op_lower in {"*", "/"}:
        return 9, 10
    return 0, 0
