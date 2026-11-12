# ----------------------------------
# Matcher 모듈
#
# 역할:
# - HTTP 응답을 템플릿의 Matcher 규칙과 비교하여
#   status / word 조건의 일치 여부를 판정한다.
#
# 주요 데이터 구조:
# - ResponseData : HTTP 응답 데이터
# - MatcherRule  : Matcher 검사 규칙
# - MatchResult  : Matcher 실행 결과
#
# 주요 함수:
# - match_status()     : HTTP 상태 코드 검사
# - match_words()      : HTTP 응답 본문의 단어 검사
# - run_matchers()     : Matcher type에 따라 개별 검사 실행
# - evaluate_matchers(): 여러 Matcher 결과를 AND/OR 조건으로 최종 판정
#
# dataclass:
# - 데이터 저장용 클래스의 __init__ 등을 자동으로 생성한다.
#
# field(default_factory=dict):
# - 객체마다 독립적인 dict를 생성하여
#   mutable 객체가 여러 인스턴스에서 공유되는 것을 방지한다.
# ----------------------------------

from dataclasses import dataclass, field


# Matcher가 사용할 HTTP 응답 데이터를 저장한다.
@dataclass
class ResponseData:
    # 서버가 반환한 HTTP 상태 코드
    # 예: 200, 404, 500
    status_code: int

    # 서버가 반환한 HTTP 응답 본문
    # word matcher의 문자열 검사에 사용한다.
    text: str

    # 서버가 반환한 HTTP 응답 헤더
    # 각 ResponseData 객체마다 독립적인 dict를 생성한다.
    headers: dict[str, str] = field(default_factory=dict)


# YAML 템플릿에서 읽어온 Matcher 검사 조건을 저장한다.
@dataclass
class MatcherRule:
    # Matcher 종류
    # 현재 지원: "status", "word"
    type: str

    # status matcher에서 허용할 HTTP 상태 코드 목록
    # 예: [200, 302, 404]
    status: list[int]

    # word matcher에서 검사할 문자열 목록
    # 예: ["Admin", "Dashboard"]
    words: list[str]

    # 하나의 word matcher 내부에서 여러 단어를 결합하는 조건
    # "and": 모든 단어가 존재해야 성공
    # "or" : 하나 이상의 단어가 존재하면 성공
    condition: str


# 여러 Matcher 실행 후 최종 판정 결과를 저장한다.
@dataclass
class MatchResult:
    # 전체 Matcher 조건의 최종 성공 여부
    matched: bool

    # 개별적으로 성공한 Matcher 종류
    # 예: ["status", "word"]
    matched_by: list[str]


# HTTP 응답 상태 코드가 템플릿의 status matcher 조건에 포함되는지 검사한다.
def match_status(response, rule):
    # 예:
    # response.status_code = 200
    # rule.status = [200, 302]
    # → 200이 목록에 포함되므로 True
    return response.status_code in rule.status


# HTTP 응답 본문에 템플릿의 word matcher 단어가 포함되는지 검사한다.
def match_words(response, rule):
    # 각 단어의 검사 결과를 저장한다.
    result = []

    # 템플릿에 정의된 단어를 하나씩 응답 본문에서 검색한다.
    for word in rule.words:
        is_matched = word in response.text
        result.append(is_matched)

    # 모든 단어가 존재해야 성공
    if rule.condition == "and":
        return all(result)

    # 하나 이상의 단어가 존재하면 성공
    elif rule.condition == "or":
        return any(result)

    # 지원하지 않는 condition 값
    else:
        raise ValueError("Unsupported matcher condition")


# Matcher type에 따라 적절한 검사 함수를 실행한다.
def run_matchers(response, rule):
    if rule.type == "status":
        return match_status(response, rule)

    elif rule.type == "word":
        return match_words(response, rule)

    # 현재 지원하지 않는 Matcher type
    else:
        raise ValueError("Unsupported matcher type")


# 여러 Matcher를 실행하고 matchers-condition에 따라 최종 결과를 판정한다.
def evaluate_matchers(response, rules, matchers_condition):
    # 각 Matcher의 True/False 결과
    results = []

    # 개별적으로 성공한 Matcher 종류
    matched_by = []

    # Matcher 규칙을 하나씩 실행한다.
    for rule in rules:
        is_matched = run_matchers(response, rule)
        results.append(is_matched)

        # 성공한 Matcher의 type을 기록한다.
        if is_matched:
            matched_by.append(rule.type)

    # 모든 Matcher가 성공해야 최종 성공
    if matchers_condition == "and":
        matched = all(results)

    # 하나 이상의 Matcher가 성공하면 최종 성공
    elif matchers_condition == "or":
        matched = any(results)

    # 지원하지 않는 matchers-condition 값
    else:
        raise ValueError("Unsupported matchers condition")

    # 최종 판정 결과와 성공한 Matcher 정보를 반환한다.
    return MatchResult(
        matched=matched,
        matched_by=matched_by
    )