"""3~9단계: HTTPRequestRule + target -> RenderedRequest 스트림.

  rule.path --(변수 치환)--> RenderedRequest (http팀으로 넘길, 바로 전송 가능한 요청)
engine이 generate_requests()를 호출해 요청을 하나씩 받아 http_client로 보낸다.
동기 제너레이터 · 무상태(vars 인자 전달) · 불변(새 객체) · 미해결이면 스킵.
"""
import re
from urllib.parse import urlsplit

from models import HTTPRequestRule, RenderedRequest

_UNRESOLVED = re.compile(r"\{\{.*?\}\}")       # 아직 안 치환된 {{...}} 찾기용


# ③ 변수 생성: target URL -> {{BaseURL}} 등
def build_vars(target: str) -> dict:
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


# {{X}} -> 값.  str.replace 라서 경로 정규화 안 됨 = traversal 페이로드 보존
# str로 치환.
def _substitute(text: str, vars: dict) -> str:
    for key, val in vars.items():
        text = text.replace("{{" + key + "}}", val)
    return text


# ⑨ 아직 {{...}} 가 남았나? (str / dict / None 다 받음)
def _has_unresolved(*parts) -> bool:
    for p in parts:
        if p is None:
            continue
        if isinstance(p, dict):
            p = "".join(str(v) for v in p.values())
        if _UNRESOLVED.search(str(p)):
            return True
    return False


# ⑥ 한 path -> 치환 -> RenderedRequest (미해결이면 None = 스킵)
def _render(path: str, rule: HTTPRequestRule, vars: dict): # (path: 요청, rule: 데이터클래스(템플릿), vars: URL... 등)
    method  = _substitute(rule.method, vars)
    url     = _substitute(path, vars)
    headers = {k: _substitute(v, vars) for k, v in rule.headers.items()}
    body    = _substitute(rule.body, vars) if rule.body else None

    if _has_unresolved(method, url, headers, body):      # ⑨ skip-not-raise
        return None
    return RenderedRequest(method=method, url=url, headers=headers, body=body)


# ⑦ raw 텍스트 -> (method, path, headers, body).  치환은 호출 전에 끝난 상태.
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


# raw 하나 -> 치환 -> 분리 -> RenderedRequest (미해결이면 None = 스킵)
def _render_raw(raw_text: str, vars: dict):
    rendered = _substitute(raw_text, vars)                   # 먼저 통째로 치환
    if _has_unresolved(rendered):                            # ⑨ skip-not-raise
        return None
    method, path, headers, body = _parse_raw(rendered)       # ⑦ 분리
    host = headers.get("Host") or vars.get("Hostname", "")   # URL 조립용 호스트
    url = f"{vars['Scheme']}://{host}{path}"                 # scheme + host + path 재조립
    return RenderedRequest(method=method, url=url, headers=headers, body=body)


# 진입점: engine이 호출. rule + target -> RenderedRequest 하나씩 yield
def generate_requests(rule: HTTPRequestRule, target: str):
    vars = build_vars(target)                  # ③ 변수 생성 (타깃당 1번)
    # ④ path/raw 분기 (rule은 둘 중 하나만 참 → 한 루프만 돎)
    for path in rule.path:                     # ⑤ path 반복
        req = _render(path, rule, vars)        # ⑥ 치환 (+⑨ 검사)
        if req is not None:
            yield req                          #    다음 단계로 하나씩
    for raw_text in rule.raw:                  # ⑧ raw 반복
        req = _render_raw(raw_text, vars)      # ⑦ 분리+치환 (+⑨ 검사)
        if req is not None:
            yield req


if __name__ == "__main__":
    # CNVD 템플릿으로 3~9단계 동작 확인
    from pathlib import Path
    from template_loader import load_template

    tpl = load_template(str(Path(__file__).parent / "http" / "CNVD-2019-01348.yaml"))
    for rule in tpl.requests:
        for req in generate_requests(rule, "https://10.0.0.1"):
            print(req)
