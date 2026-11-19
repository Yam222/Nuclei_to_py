"""공용 모듈 (프로토콜·매처 공용).

팀원은 여기서만 import 하면 된다 (안쪽 파일 구조가 바뀌어도 import 줄은 그대로):
    from scanner.core.common import build_context, render_text, evaluate_dsl

    expressions.py  {{ }} 계산기 + render_text
    variables.py    build_context (variables: 블록 -> ctx)
    dsl.py          evaluate_dsl (dsl 매처 식 -> True/False)
    helpers.py      {{ }}·dsl 안에서 부르는 함수 목록
"""
from scanner.core.common.expressions import render_text, render_text_verbose
from scanner.core.common.variables import build_context
from scanner.core.common.dsl import evaluate_dsl, evaluate_dsl_verbose

__all__ = [
    "build_context",
    "render_text", "render_text_verbose",
    "evaluate_dsl", "evaluate_dsl_verbose",
]
