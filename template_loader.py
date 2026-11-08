"""1~2단계: YAML 템플릿 파일 -> Template 객체.

  YAML 텍스트 --(yaml.safe_load: 1단계)--> dict --(_parse_*: 2단계)--> Template
PyYAML이 '텍스트 -> dict'를, 이 파일이 'dict -> 객체'를 담당한다.
MVP가 쓰는 필드만 꺼내고, 모르는 키(classification/metadata/reference 등)는
.get()이 알아서 흘려보낸다.
"""
import yaml

from models import Template, Info, HTTPRequestRule, Matcher


class UnsupportedProtocolError(Exception):
    """http 외 프로토콜 템플릿 (아직 미구현 -> 스킵)."""


# 아는 프로토콜 키 (감지/로그용)
_PROTOCOL_KEYS = ("dns", "network", "tcp", "ssl", "file",
                  "headless", "websocket", "whois", "code", "javascript")

# 템플릿 로드
def load_template(path: str) -> Template:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)          # 1단계: YAML -> dict
    return _parse_template(data)          # 2단계: dict -> Template

# models.py의 @dataclass class Template 반환
def _parse_template(data: dict) -> Template:
    requests: list = []          # 여러 프로토콜 공용 큐 (Nuclei의 []protocols.Request 대응)

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

    # 아무 프로토콜도 안 걸림 = Nuclei의 "no requests defined"
    if not requests:
        raise UnsupportedProtocolError(_detect_protocol(data))

    return Template(
        id=data.get("id", ""),
        info=_parse_info(data.get("info", {})),
        requests=requests,
    )

# models.py의 @dataclass class Info 반환
def _parse_info(d: dict) -> Info:
    return Info(
        name=d.get("name", ""),
        severity=d.get("severity", ""),
    )

# models.py의 @dataclass class HTTPRequestRule 반환
def _parse_request(d: dict) -> HTTPRequestRule:
    return HTTPRequestRule(
        method=d.get("method", "GET"),
        path=d.get("path", []),
        raw=d.get("raw", []),
        headers=d.get("headers", {}),
        body=d.get("body"),
        matchers=[_parse_matcher(m) for m in d.get("matchers", [])],
        matchers_condition=d.get("matchers-condition", "or"),   # 하이픈 키 -> 언더스코어 필드
    )

# models.py의 @dataclass class Matcher 반환
def _parse_matcher(d: dict) -> Matcher:
    return Matcher(
        type=d.get("type", ""),
        part=d.get("part", "body"),
        words=d.get("words", []),
        regex=d.get("regex", []),
        status=d.get("status", []),
        condition=d.get("condition", "or"),
    )


# http도 없고 지원 프로토콜도 없을 때, 뭐였는지 알려주기 위함
def _detect_protocol(data: dict) -> str:
    for key in _PROTOCOL_KEYS:
        if key in data:
            return key
    return "unknown"


# 프로토콜별 파서: http(_parse_request)만 구현, 나머지는 빈 스텁
# 나중에 각 프로토콜 구현하면 여기 채우고 자기 Rule 타입을 반환
def _parse_dns(block: list) -> list:       # TODO: DNS
    return []

def _parse_network(block: list) -> list:   # TODO: Network/TCP
    return []

def _parse_ssl(block: list) -> list:       # TODO: SSL
    return []

def _parse_file(block: list) -> list:      # TODO: File
    return []

def _parse_headless(block: list) -> list:  # TODO: Headless
    return []

def _parse_code(block: list) -> list:      # TODO: Code
    return []


if __name__ == "__main__":
    # 루트 폴더의 템플릿으로 1~2단계 동작 확인
    tpl = load_template("CNVD-2019-01348.yaml")
    print(tpl)
