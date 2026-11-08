"""
공유 데이터 모델. (1~2단계 산출물 = Template)

MVP가 쓰는 필드만 담는다. 모르는 YAML 키는 로더가 흘려보낸다.
RenderedRequest(http팀으로 넘기는 출력 계약)·ScanResult(결과)는
각 담당 단계에서 나중에 이 파일에 추가.
"""
from dataclasses import dataclass, field

# 응답 판정 조건 하나 (매처팀이 실행)
@dataclass
class Matcher:
    type: str                                           # "status" | "word" | "regex"
    part: str = "body"                                  # 응답의 어디를 볼지 (body/header/all)
    words: list[str] = field(default_factory=list)
    regex: list[str] = field(default_factory=list)
    status: list[int] = field(default_factory=list)
    condition: str = "or"                               # 한 매처 안 값들의 and/or

# 요청 하나: 보낼 재료(method~body) + 응답 판정(matchers)
@dataclass
class HTTPRequestRule:
    method: str = "GET"
    path: list[str] = field(default_factory=list)       # path 템플릿
    raw: list[str] = field(default_factory=list)        # raw 템플릿 (path와 둘 중 하나만 참)
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    matchers: list[Matcher] = field(default_factory=list)
    matchers_condition: str = "or"                      # 매처들 사이 and/or (YAML: matchers-condition)


# 출력/리포트용
@dataclass
class Info:
    name: str = ""      # 이름
    severity: str = ""  # 심각도


# 템플릿(YAML)을 3블록으로 나눔
@dataclass
class Template:
    id: str             # 식별(id)
    info: Info          # 메타(info)
    requests: list[HTTPRequestRule] = field(default_factory=list)   # 실제 실행할 내용(http)


# 출력 계약: generator(3~9) → http팀. 치환 끝나 바로 전송 가능한 요청.
@dataclass
class RenderedRequest:
    method: str                                    # HTTP 메서드 (GET/POST...)
    url: str                                       # 변수 치환 완료된 타겟 URL
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
