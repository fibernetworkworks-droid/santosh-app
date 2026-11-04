---
name: byox-programming-language
description: Build an interpreter: lexer, Pratt parser, AST evaluator, closures
---
GOAL: a working interpreter for a small language with closures and first-class functions.

PHASES
1. Lexer: tokenise integers, strings, operators, keywords; skip whitespace.
2. Pratt parser: left-binding power for correct precedence; build AST nodes.
3. Tree-walk evaluator: literals, binary ops, variables, if/else.
4. Functions + closures: lexical scoping via environment chain (outer pointer).
5. Built-in types (arrays, maps); `len`, `push`, `puts`; tail-call optimisation.

CORE CONCEPTS
- Pratt parsing: each token has nud (prefix) and led (infix) parse functions.
- Environment: map of name→value + pointer to outer scope; lookup walks chain.
- Closure: captures its defining environment, not a copy — mutating outer works.

VERIFY: recursive fibonacci(10) returns 55; closures capture correctly.
