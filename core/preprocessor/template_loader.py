"""preprocessor: YAML 템플릿 파일 -> Template 객체.

--------------------------------------------
메인에서 load_template( 템플릿 경로 )함수 실행
Template 반환
--------------------------------------------

load_template(path: str) -> Template

@dataclass
class Template:
    id: str
    info: Info
    requests: list[ProtocolRequest] = field(default_factory=list)

# 모든 프로토콜 요청의 공통 베이스("인터페이스"). 하위가 상속.
@dataclass
class ProtocolRequest:
    protocol: ClassVar[str] = ""        # 하위가 덮어씀 = 팩토리 분기 키

# 요청 하나: 보낼 재료(method~body) + 응답 판정(matchers)
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

models.py 참고
"""
import yaml

from scanner.types.models import Template, Info, HTTPRequestRule, MatcherRule


class UnsupportedProtocolError(Exception):
    """http 외 프로토콜 템플릿 (아직 미구현 -> 스킵)."""


# 아는 프로토콜 키 (감지/로그용)
_PROTOCOL_KEYS = ("dns", "network", "tcp", "ssl", "file",
                  "headless", "websocket", "whois", "code", "javascript")


def load_template(path: str) -> Template:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)          # 1단계: YAML -> dict
    return _parse_template(data)          # 2단계: dict -> Template

def _parse_template(data: dict) -> Template:
    requests: list = []          # 여러 프로토콜 공용 큐

    # HTTP -- 유일하게 구현됨 ('requests'는 구버전 http 키)
    raw_http = data.get("http") or data.get("requests")
    if raw_http:
        requests += [_parse_request(r) for r in raw_http]

    # 그 외 프로토콜 -- 지금은 빈 스텁이라 아무것도 안 더해짐 -> 스킵됨
    if "dns" in data:
        requests += _parse_dns(data["dns"])
    if "network" in data or "tcp" in data:
        requests += _parse_network(data.get("network") or data.get("tcp"))
    if "ssl" in data:
        requests += _parse_ssl(data["ssl"])
    if "file" in data:
        requests += _parse_file(data["file"])
    if "headless" in data:
        requests += _parse_headless(data["headless"])
    if "code" in data:
        requests += _parse_code(data["code"])

    if not requests:
        raise UnsupportedProtocolError(_detect_protocol(data))

    return Template(
        id=data.get("id", ""),
        info=_parse_info(data.get("info", {})),
        requests=requests,
        variables={str(k): str(v) for k, v in (data.get("variables") or {}).items()},   # 원문만 담음 (랜덤 계산 X)
    )


def _detect_protocol(data: dict) -> str:
    for key in _PROTOCOL_KEYS:
        if key in data:
            return key
    return "unknown"


def _parse_info(d: dict) -> Info:
    return Info(name=d.get("name", ""), severity=d.get("severity", ""))

# MatcherRule(매처팀 타입) 반환 -- YAML 키를 그대로 옮김 (하이픈 키 -> 언더스코어)
# 값의 해석(part 기본값, regex/dsl 실행 등)은 매처팀 몫. 로더는 원문만 담는다.
def _parse_matcher(d: dict) -> MatcherRule:
    return MatcherRule(
        type=d.get("type", ""),
        status=[int(x) for x in _as_list(d.get("status"))],
        words=[str(x) for x in _as_list(d.get("words"))],
        condition=d.get("condition", "or"),
        part=d.get("part", ""),
        negative=bool(d.get("negative", False)),
        size=[int(x) for x in _as_list(d.get("size"))],
        regex=[str(x) for x in _as_list(d.get("regex"))],
        binary=[str(x) for x in _as_list(d.get("binary"))],
        dsl=[str(x) for x in _as_list(d.get("dsl"))],
        xpath=[str(x) for x in _as_list(d.get("xpath"))],
        name=d.get("name", ""),
        encoding=d.get("encoding", ""),
        case_insensitive=bool(d.get("case-insensitive", False)),   # 하이픈 키
        match_all=bool(d.get("match-all", False)),                 # 하이픈 키
        internal=bool(d.get("internal", False)),
    )


# YAML에서 목록 자리에 값 하나만 오거나(words: abc) 비어 있어도(None) 항상 list로
def _as_list(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


# 프로토콜별 파서: http만 구현, 나머지는 빈 스텁 (나중에 채우고 자기 Rule 반환)

#http
def _parse_request(d: dict) -> HTTPRequestRule:
    return HTTPRequestRule(
        method=d.get("method", "GET"),
        path=d.get("path", []),
        raw=d.get("raw", []),
        headers=d.get("headers", {}),
        body=d.get("body"),
        matchers=[_parse_matcher(m) for m in d.get("matchers", [])],
        matchers_condition=d.get("matchers-condition", "or"),   # 하이픈 키 -> 언더스코어
    )
def _parse_dns(block: list) -> list:       return []   # TODO: DNS
def _parse_network(block: list) -> list:   return []   # TODO: Network/TCP
def _parse_ssl(block: list) -> list:       return []   # TODO: SSL
def _parse_file(block: list) -> list:      return []   # TODO: File
def _parse_headless(block: list) -> list:  return []   # TODO: Headless
def _parse_code(block: list) -> list:      return []   # TODO: Code
