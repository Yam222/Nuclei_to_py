"""식 계산기 + {{ }} 치환 (Nuclei: protocols/common/expressions).

--------------------------------------------
공개 함수
  render_text(text, ctx)           -> text 안의 {{...}} 를 전부 채운 문자열
                                      하나라도 못 채우면 None (= 그 요청 스킵)
내부 계산기(_evaluate)는 같은 패키지의 variables.py / dsl.py 도 함께 쓴다.
--------------------------------------------

{{ }} 안에서 지원하는 문법 (dsl 식도 같은 문법)
  변수        BaseURL, payload
  문자열      'abc'  "abc"
  숫자        6  111
  함수 호출   rand_base(6)  to_lower(rand_base(2))   (중첩 OK, helpers.HELPERS 에 있는 것만)
  이어붙이기  username + ':' + password
  비교        ==  !=  >  <  >=  <=      (한쪽이 숫자면 숫자로 비교: status_code == "200" OK)
  논리        &&  ||  !                 (단락 평가: 왼쪽으로 결과가 정해지면 오른쪽은 계산 안 함)
  괄호        ( ... )
그 외(*, -, ?: 등)는 지원 안 함 -> 평가 실패 -> None (dsl 이면 False)

※ eval() 안 씀. 직접 만든 작은 파서로 허용된 것만 처리한다.
"""
import operator
import re

from scanner.core.common.helpers import HELPERS, HelperNotImplemented

_EXPR = re.compile(r"\{\{(.*?)\}\}", re.S)      # 텍스트 안의 {{ ... }} 찾기


# 텍스트 안의 {{...}} 전부 채우기. 하나라도 실패하면 None
def render_text(text, ctx: dict):
    value, _reason = render_text_verbose(text, ctx)
    return value


# render_text 와 같지만 실패 이유도 돌려줌 (디버그/테스트용)
def render_text_verbose(text, ctx: dict):
    if text is None:
        return None, "텍스트 없음"
    errors = []

    def _replace(m):
        try:
            return _to_str(_evaluate(m.group(1), ctx))
        except _EvalError as e:
            errors.append(str(e))
            return m.group(0)

    out = _EXPR.sub(_replace, str(text))          # {{ }} 밖의 글자는 그대로 (traversal 보존)
    if errors:
        return None, errors[0]
    return out, None


# ─────────────────────────────────────────────
# 내부: 식 하나 평가 (토큰 분리 -> 재귀 파서)   ※ dsl.py 도 _evaluate / _EvalError 사용
# ─────────────────────────────────────────────
class _EvalError(Exception):
    pass


_TOKEN = re.compile(r"""
    \s*(?:
        (?P<str>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")    # 문자열
      | (?P<num>\d+)                                    # 숫자
      | (?P<name>[A-Za-z_][A-Za-z0-9_-]*)               # 변수/함수 이름
      | (?P<op>==|!=|>=|<=|&&|\|\||[(),+<>!])           # 기호 (두 글자짜리 먼저)
    )""", re.X)


def _tokenize(expr: str) -> list:
    tokens, pos, expr = [], 0, expr.strip()
    while pos < len(expr):
        m = _TOKEN.match(expr, pos)
        if not m or m.end() == pos:
            raise _EvalError(f"해석할 수 없는 식: {expr!r}")
        kind = m.lastgroup
        tokens.append((kind, m.group(kind)))
        pos = m.end()
        while pos < len(expr) and expr[pos].isspace():
            pos += 1
    return tokens


def _evaluate(expr: str, ctx: dict):
    parser = _Parser(_tokenize(expr), ctx)
    value = parser.expr()
    if parser.peek() is not None:
        raise _EvalError(f"해석할 수 없는 식: {expr.strip()!r}")
    return value


class _Parser:
    def __init__(self, tokens, ctx):
        self.tokens, self.i, self.ctx = tokens, 0, ctx
        self.skip = 0       # > 0 이면 "읽기만 하고 계산 안 함" (단락 평가로 버려지는 쪽)

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self):
        tok = self.peek()
        if tok is None:
            raise _EvalError("식이 중간에 끝남")
        self.i += 1
        return tok

    def expect(self, op):
        tok = self.take()
        if tok != ("op", op):
            raise _EvalError(f"'{op}' 가 필요함")

    # 우선순위 (아래로 갈수록 먼저 계산):  ||  <  &&  <  !  <  비교  <  +  <  값 하나
    # expr := and_expr ('||' and_expr)*
    def expr(self):
        value = self.and_expr()
        while self.peek() == ("op", "||"):
            self.take()
            if value:                                  # 이미 True -> 오른쪽은 읽기만
                self._skip_parse(self.and_expr)
                value = True
            else:
                value = bool(self.and_expr())
        return value

    # and_expr := not_expr ('&&' not_expr)*
    def and_expr(self):
        value = self.not_expr()
        while self.peek() == ("op", "&&"):
            self.take()
            if not value:                              # 이미 False -> 오른쪽은 읽기만
                self._skip_parse(self.not_expr)
                value = False
            else:
                value = bool(self.not_expr())
        return value

    # not_expr := '!' not_expr | compare
    def not_expr(self):
        if self.peek() == ("op", "!"):
            self.take()
            value = self.not_expr()
            return None if self.skip else not bool(value)
        return self.compare()

    # compare := add (('=='|'!='|'>'|'<'|'>='|'<=') add)?
    def compare(self):
        left = self.add()
        tok = self.peek()
        if tok and tok[0] == "op" and tok[1] in _COMPARE:
            self.take()
            right = self.add()
            if self.skip:
                return None
            a, b = _coerce(left, right)
            return _COMPARE[tok[1]](a, b)
        return left

    # add := term ('+' term)*
    def add(self):
        value = self.term()
        while self.peek() == ("op", "+"):
            self.take()
            right = self.term()
            if self.skip:
                value = None
            elif isinstance(value, int) and not isinstance(value, bool) \
                    and isinstance(right, int) and not isinstance(right, bool):
                value = value + right                      # 숫자끼리는 덧셈
            else:
                value = _to_str(value) + _to_str(right)    # 그 외는 이어붙이기
        return value

    # 단락 평가: 결과에 안 쓰이는 쪽은 문법만 읽고(토큰 소비) 변수 조회·함수 실행은 안 함
    def _skip_parse(self, rule):
        self.skip += 1
        try:
            rule()
        finally:
            self.skip -= 1

    # term := 문자열 | 숫자 | 변수 | 함수호출 | ( expr )
    def term(self):
        kind, text = self.take()
        if kind == "str":
            return re.sub(r"\\(.)", r"\1", text[1:-1])
        if kind == "num":
            return int(text)
        if kind == "name":
            if self.peek() == ("op", "("):
                return self.call(text)
            if text in self.ctx:
                return self.ctx[text]
            if self.skip:                              # 버려지는 쪽이면 몰라도 OK
                return None
            raise _EvalError(f"모르는 변수: {text}")
        if (kind, text) == ("op", "("):
            value = self.expr()
            self.expect(")")
            return value
        raise _EvalError(f"예상치 못한 기호: {text}")

    # call := name '(' [expr (',' expr)*] ')'
    def call(self, name):
        fn = HELPERS.get(name)
        if fn is None and not self.skip:
            raise _EvalError(f"모르는 함수: {name}")
        self.expect("(")
        args = []
        if self.peek() != ("op", ")"):
            args.append(self.expr())
            while self.peek() == ("op", ","):
                self.take()
                args.append(self.expr())
        self.expect(")")
        if self.skip:                                  # 버려지는 쪽이면 실행 안 함
            return None
        try:
            return fn(*args)
        except HelperNotImplemented:
            raise _EvalError(f"미구현 헬퍼: {name}")
        except Exception as e:                     # 인자 개수/형식 오류 등
            raise _EvalError(f"{name} 실행 오류: {e}")


def _to_str(value) -> str:
    if isinstance(value, bool):                        # True/False -> "true"/"false"
        return "true" if value else "false"
    return value if isinstance(value, str) else str(value)


# 비교 연산자 -> 파이썬 함수
_COMPARE = {"==": operator.eq, "!=": operator.ne, ">": operator.gt,
            "<": operator.lt, ">=": operator.ge, "<=": operator.le}


# 비교 전 형 맞추기: 한쪽이 숫자면 둘 다 숫자로 (status_code == "200" 도 참)
def _coerce(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a), bool(b)
    if isinstance(a, int) or isinstance(b, int):
        try:
            return int(a), int(b)
        except (TypeError, ValueError):
            pass
    return _to_str(a), _to_str(b)
