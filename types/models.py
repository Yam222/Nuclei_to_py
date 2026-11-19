"""공유 데이터 모델 (types).
- 입력 모델(Template/Info/ProtocolRequest/HTTPRequestRule/MatcherRule): dataclass
- 출력 계약(RenderedHTTPRequest): Pydantic — Engine 팀과 '동일 타입/이름'
"""
from dataclasses import dataclass, field
from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, Field


# 매처 종류 (Nuclei matcher type 7종)  ※ 매처팀에서 정의를 받으면 그걸로 교체
MatcherType = Literal["word", "regex", "status", "size", "binary", "dsl", "xpath"]


# YAML 템플릿에서 읽어온 Matcher 검사 조건 (매처팀 공유 타입)
@dataclass
class MatcherRule:
    # 기본 정보
    # 현재 규칙에서 실행할 Matcher 종류다.
    type: MatcherType
    # status Matcher에서 허용할 HTTP 상태 코드 목록이다.
    status: list[int] = field(default_factory=list)
    # word Matcher에서 찾을 문자열 목록이다.
    words: list[str] = field(default_factory=list)
    # 하나의 Matcher 안에 여러 검사값이 있을 때 적용할 조건이다.
    condition: Literal["or", "and"] = "or"
    # 검사할 응답 부분이다. 예: body, header, all
    part: str = ""
    # True이면 원래 검사 결과를 반대로 뒤집는다.
    negative: bool = False

    # Matcher별 검사값
    # size Matcher에서 허용할 응답 크기 목록이다.
    size: list[int] = field(default_factory=list)
    # regex Matcher에서 사용할 정규표현식 목록이다.
    regex: list[str] = field(default_factory=list)
    # binary Matcher에서 사용할 16진수 패턴 목록이다.
    binary: list[str] = field(default_factory=list)
    # DSL Matcher에서 사용할 조건식 목록이다.
    dsl: list[str] = field(default_factory=list)
    # XPath Matcher에서 사용할 XPath 표현식 목록이다.
    xpath: list[str] = field(default_factory=list)
    # Matcher를 구별하기 위한 선택적인 이름이다.
    name: str = ""

    # 세부 동작 설정
    # word 값을 해석할 인코딩 방식이다. 예: hex
    encoding: str = ""
    # True이면 word Matcher에서 대소문자를 구분하지 않는다.
    case_insensitive: bool = False
    # True이면 모든 검사값이 일치해야 한다.
    match_all: bool = False
    # True이면 Matcher 결과를 외부 결과에 표시하지 않는다.
    internal: bool = False


# 출력/리포트용 메타
@dataclass
class Info:
    name: str = ""
    severity: str = ""


# 모든 프로토콜 요청의 공통 베이스("인터페이스"). 하위가 상속.
@dataclass
class ProtocolRequest:
    protocol: ClassVar[str] = ""        # 하위가 덮어씀 = 팩토리 분기 키


# http 프로토콜
# ProtocolRequest를 부모로 함.
@dataclass
class HTTPRequestRule(ProtocolRequest):
    protocol: ClassVar[str] = "http"
    method: str = "GET"
    path: list[str] = field(default_factory=list)        # path 템플릿
    raw: list[str] = field(default_factory=list)         # raw 템플릿 (path와 둘 중 하나만)
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    matchers: list[MatcherRule] = field(default_factory=list)
    matchers_condition: str = "or"                       # 매처들 사이 and/or (YAML: matchers-condition)


# 템플릿(YAML) 전체 = id + info + 요청들 (여러 프로토콜 담을 수 있게 베이스 타입)
@dataclass
class Template:
    id: str
    info: Info
    requests: list[ProtocolRequest] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)   # YAML variables: 원문 그대로 (계산은 실행 시 build_context)


# 출력 계약: http_compiler → http팀(Engine). 치환 끝나 바로 전송 가능한 요청.
class RenderedHTTPRequest(BaseModel):
    method: str
    url: str
    headers: dict = Field(default_factory=dict)
    body: Optional[str] = None
