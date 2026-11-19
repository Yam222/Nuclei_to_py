"""dsl 매처 식 판정 -> True/False (Nuclei: operators/common/dsl).

--------------------------------------------
공개 함수
  evaluate_dsl(expr, vars)  -> dsl 식 하나를 True/False 로 (못 읽으면 False)
                               vars = ctx | 응답 변수(status_code, body, header, content_type ...)
                               식 안의 {{ }} 는 먼저 치환한 뒤 계산

예)  evaluate_dsl('status_code == 200 && contains(body, "{{marker}}")', ctx | resp_vars)
문법은 expressions.py 와 같음 (비교 == != > < >= <=, 논리 && || !, 함수는 helpers.py)
--------------------------------------------
"""
from scanner.core.common.expressions import render_text_verbose, _evaluate, _EvalError


# dsl 매처용: 식 하나 -> True/False. 못 읽는 식이면 False
#   식 안에 {{marker}} 가 있으면 같은 vars 로 먼저 치환한 뒤 계산 (매처팀은 신경 안 써도 됨)
def evaluate_dsl(expr: str, vars: dict) -> bool:
    return evaluate_dsl_verbose(expr, vars)[0]


# evaluate_dsl 과 같지만 실패 이유도 돌려줌 (디버그/테스트용)
def evaluate_dsl_verbose(expr: str, vars: dict):
    expr = str(expr)
    if "{{" in expr:                                   # ① 치환: 'contains(body, "{{marker}}")'
        expr, why = render_text_verbose(expr, vars)    #     -> 'contains(body, "S8A1Nu")'
        if expr is None:
            return False, why
    try:                                               # ② 계산
        return bool(_evaluate(expr, vars)), None
    except _EvalError as e:
        return False, str(e)
