"""템플릿 variables: 블록 계산 -> ctx(변수 장부) 생성 (Nuclei: protocols/common/variables).

--------------------------------------------
공개 함수
  build_context(template, base_vars) -> base_vars + template.variables 계산값
                                        base_vars = 프로토콜 기본 변수 (HTTP: build_http_vars(target))
                                        템플릿·타겟당 1번만 호출 (랜덤값이 여기서 확정)
--------------------------------------------
"""
from scanner.core.common.expressions import render_text


# base_vars(프로토콜 기본 변수) 위에 variables: 블록을 위에서부터 계산해 쌓음. 템플릿당 1번!
# base_vars 는 각 프로토콜이 만들어 넘김 (HTTP: http_compiler.build_http_vars)
def build_context(template, base_vars: dict) -> dict:
    ctx = dict(base_vars)                      # 복사본 (넘겨받은 base_vars 는 안 건드림)
    pending = dict(getattr(template, "variables", None) or {})
    # 변수가 다른 변수를 참조할 수 있으므로, 계산되는 것부터 채우며 반복
    while pending:
        progressed = False
        for name in list(pending):
            value = render_text(pending[name], ctx)
            if value is not None:
                ctx[name] = value
                del pending[name]
                progressed = True
        if not progressed:      # 남은 건 계산 불가(미구현 헬퍼·모르는 변수) -> ctx에 안 넣음
            break               # -> 그 변수를 쓰는 요청은 render_text가 None -> 스킵
    return ctx
