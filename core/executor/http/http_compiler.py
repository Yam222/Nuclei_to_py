"""http_compiler: HTTPRequestRule + target -> RenderedHTTPRequest 스트림.
동기 제너레이터 · 무상태(vars 인자 전달) · 불변(새 객체) · 미해결이면 스킵.

--------------------------------------------
메인 사용 방법
from scanner.core.preprocessor.template_loader import load_template, UnsupportedProtocolError
from scanner.core.executor.http.http_compiler import build_http_vars, generate_requests
from scanner.core.common import build_context, render_text

target = "http://127.0.0.1:8080"                     # 호스트 루트까지만 (페이지 경로 X)

tpl = load_template("templet/http/variables/CVE-2026-28141.yaml")   # ① YAML -> Template
ctx = build_context(tpl, build_http_vars(target))                    # ② 변수 장부 (템플릿·타겟당 1번)

for rule in tpl.requests:                                            # ③ 요청 규칙 하나씩
    for req in generate_requests(rule, ctx):                         # ④ RenderedHTTPRequest 하나씩
        resp = send(req)                                             # ⑤ 전송 (http_requester, 신규 B)
        for m in rule.matchers:                                      # ⑥ 판정 (매처팀)
            words = [render_text(w, ctx) for w in m.words]           #    같은 ctx로 {{marker}} 채우기
            ...

            
메인에서 generate_requests(rule: HTTPRequestRule, ctx: dict | str) ->  RenderedHTTPRequets 실행
yield로 RenderedHTTPRequest 반환

반환형 
class RenderedHTTPRequest(BaseModel):
    method: str
    url: str
    headers: dict = Field(default_factory=dict)
    body: Optional[str] = None

--------------------------------------------
generate_requests(rule: HTTPRequestRule, ctx: dict | str) -> Iterator[RenderedHTTPRequest]
"""
from typing import Iterator
from urllib.parse import urlsplit

from scanner.types.models import HTTPRequestRule, RenderedHTTPRequest
# 치환(render_text)은 공용 모듈 (매처팀도 같은 함수 사용). URL 변수 생성은 HTTP 전용이라 여기 둠
from scanner.core.common import render_text


# ③ HTTP 기본 변수(base_vars): target URL -> {{BaseURL}} 등
#    main: ctx = build_context(tpl, build_http_vars(target))
def build_http_vars(target: str) -> dict:
    u = urlsplit(target)
    netloc = u.netloc
    if "@" in netloc:                          # user:pass@host 면 앞부분 제거
        netloc = netloc.split("@", 1)[1]
    return {
        "BaseURL":  target.rstrip("/"),
        "RootURL":  f"{u.scheme}://{netloc}",
        "Hostname": netloc,                    # host:port (Host 헤더용)
        "Host":     u.hostname or "",
        "Port":     str(u.port) if u.port else "",
        "Scheme":   u.scheme,
        "Path":     u.path or "/",
    }


# 한 path -> 치환 -> RenderedHTTPRequest (미해결이면 None = 스킵)
def _render(path: str, rule: HTTPRequestRule, vars: dict):
    method  = render_text(rule.method, vars)
    url     = render_text(path, vars)
    headers = {}
    for k, v in rule.headers.items():
        hv = render_text(str(v), vars)
        if hv is None:                                   # ⑨ skip-not-raise
            return None
        headers[k] = hv
    body    = render_text(rule.body, vars) if rule.body else None
    if method is None or url is None or (rule.body and body is None):   # ⑨ skip-not-raise
        return None
    return RenderedHTTPRequest(method=method, url=url, headers=headers, body=body)


# raw 텍스트 -> (method, path, headers, body).  치환은 호출 전에 끝난 상태.
def _parse_raw(raw_text: str):
    raw_text = raw_text.replace("\r\n", "\n").lstrip("\n")   # 개행 정리
    if "\n\n" in raw_text:                                   # 첫 빈 줄 = 헤더/바디 경계
        head, body = raw_text.split("\n\n", 1)
    else:
        head, body = raw_text, None
    lines = head.splitlines()
    first = lines[0].split()                                 # "METHOD PATH HTTP/1.1"
    method = first[0]
    path = first[1] if len(first) > 1 else "/"
    headers = {}                                             # 2줄차부터 = 헤더
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip()] = v.strip()
    return method, path, headers, (body if body else None)


# raw 하나 -> 치환 -> 분리 -> RenderedHTTPRequest (미해결이면 None = 스킵)
def _render_raw(raw_text: str, vars: dict):
    rendered = render_text(raw_text, vars)                   # 먼저 통째로 치환
    if rendered is None:                                     # ⑨ skip-not-raise
        return None
    method, path, headers, body = _parse_raw(rendered)       # ⑦ 분리
    host = headers.get("Host") or vars.get("Hostname", "")   # URL 조립용 호스트
    url = f"{vars['Scheme']}://{host}{path}"                 # scheme + host + path 재조립
    return RenderedHTTPRequest(method=method, url=url, headers=headers, body=body)


# 진입점: executor가 호출. rule + target -> RenderedHTTPRequest 하나씩 yield
def generate_requests(rule: HTTPRequestRule, ctx: dict | str) -> Iterator[RenderedHTTPRequest]:
    # ctx = build_context(tpl, build_http_vars(target)) 결과 (URL 변수 + variables). 템플릿당 1번 만들어 매처와 공유.
    # 하위호환: target 문자열을 그대로 넘겨도 동작 (이 경우 variables 없이 URL 변수만)
    vars = build_http_vars(ctx) if isinstance(ctx, str) else ctx
    for path in rule.path:                     # ⑤ path 반복
        req = _render(path, rule, vars)        # ⑥ 치환 (+⑨ 검사)
        if req is not None:
            yield req                          #    다음 단계로 하나씩
    for raw_text in rule.raw:                  # ⑧ raw 반복
        req = _render_raw(raw_text, vars)      # ⑦ 분리+치환 (+⑨ 검사)
        if req is not None:
            yield req
