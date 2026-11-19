"""헬퍼 함수 목록 .

{{ }} 안에서 호출할 수 있는 함수는 여기 HELPERS에 등록된 것뿐이다.
등록 안 된 이름은 절대 실행되지 않는다 (eval 안 씀 = 안전).

- 구현됨 : XSS 템플릿에서 실제로 쓰이는 12종 (+ 옛 이름 별칭)
           + dsl 매처용 7종 (contains, contains_all, contains_any, regex, starts_with, ends_with, len)
- 정의만 : 나머지는 시그니처만 두고 HelperNotImplemented 발생
           -> 평가 실패로 처리되어 그 요청만 스킵 (스캔 전체는 안 죽음)
           필요해지면 본문만 채우면 됨

규칙: {{ }} 치환용 함수는 문자열을 반환한다 (URL/헤더/바디에 그대로 끼워 넣기 위해).
      dsl 매처용 함수는 True/False 또는 숫자(len)를 반환한다.
      숫자 인자는 함수 안에서 int()로 변환한다.
"""
import base64 as _b64
import random
import re
import string
import urllib.parse
import warnings
from datetime import datetime


class HelperNotImplemented(Exception):
    """정의만 해둔 헬퍼가 호출됨 -> 평가 실패 (요청 스킵)."""


_LETTERS = string.ascii_letters
_DIGITS = string.digits
_ALNUM = string.ascii_letters + string.digits


def _rand(charset, length, bad=""):
    pool = [c for c in str(charset) if c not in str(bad)]
    if not pool:
        raise ValueError("사용할 문자가 없음")
    return "".join(random.choice(pool) for _ in range(int(length)))


# ─────────────────────────────────────────────
# 구현됨 (XSS 템플릿에서 사용하는 12종)
# ─────────────────────────────────────────────

# 랜덤 ─ 오탐 방지용 nonce. 보통 variables: 에서 1번만 만들어 요청·매처가 공유
def rand_base(length, charset=_ALNUM):            # rand_base(6) / rand_base(7, "abc")
    return _rand(charset, length)

def rand_text_alpha(length, bad_chars=""):        # 영문자만
    return _rand(_LETTERS, length, bad_chars)

def rand_text_numeric(length, bad_numbers=""):    # 숫자만
    return _rand(_DIGITS, length, bad_numbers)

def rand_text_alphanumeric(length, bad_chars=""): # 영문+숫자
    return _rand(_ALNUM, length, bad_chars)

def rand_int(min_value=0, max_value=2147483647):  # rand_int(111, 999)
    return str(random.randint(int(min_value), int(max_value)))

# 문자열
def to_lower(s):
    return str(s).lower()

# 인코딩 / 디코딩
def url_encode(s):                                 # 페이로드를 URL에 안전하게
    return urllib.parse.quote(str(s), safe="")

def url_decode(s):
    return urllib.parse.unquote(str(s))

def base64(s):
    return _b64.b64encode(str(s).encode("utf-8")).decode("ascii")

def base64_decode(s):
    return _b64.b64decode(str(s)).decode("latin-1")   # 바이트를 1:1로 보존

def hex_decode(s):
    return bytes.fromhex(str(s)).decode("latin-1")

# 시간 ─ Nuclei 형식: %Y 년 / %M 월 / %D 일 / %H 시 / %m 분 / %s 초
def date_time(fmt, unix_time=None):
    t = datetime.fromtimestamp(int(unix_time)) if unix_time is not None else datetime.now()
    table = {"Y": f"{t.year:04d}", "M": f"{t.month:02d}", "D": f"{t.day:02d}",
             "H": f"{t.hour:02d}", "m": f"{t.minute:02d}", "s": f"{t.second:02d}"}
    return re.sub(r"%([YMDHms])", lambda m: table[m.group(1)], str(fmt))


# ─────────────────────────────────────────────
# dsl 매처용 (True/False 또는 숫자 반환)
# ─────────────────────────────────────────────
def contains(haystack, needle):                       # contains(body, "abc")
    return str(needle) in str(haystack)

def contains_all(haystack, *needles):                 # contains_all(body, "a", "b") -> 전부 있어야
    return all(str(n) in str(haystack) for n in needles)

def contains_any(haystack, *needles):                 # contains_any(body, "a", "b") -> 하나라도
    return any(str(n) in str(haystack) for n in needles)

def regex(pattern, text):                             # regex("ver ([0-9.]+)", body)
    with warnings.catch_warnings():                   # 일부 템플릿 정규식의 FutureWarning 숨김
        warnings.simplefilter("ignore", FutureWarning)
        return re.search(str(pattern), str(text)) is not None

def starts_with(s, *prefixes):                        # starts_with(body, "<?xml")
    return any(str(s).startswith(str(p)) for p in prefixes)

def ends_with(s, *suffixes):
    return any(str(s).endswith(str(p)) for p in suffixes)

def length(s):                                        # len(body) > 100
    return len(str(s))


# ─────────────────────────────────────────────
# 정의만 (TODO) ─ XSS 외 템플릿에서 쓰임. 필요해지면 본문 채우기
# ─────────────────────────────────────────────

# 해시
def md5(s):                                   raise HelperNotImplemented("md5")
def sha1(s):                                  raise HelperNotImplemented("sha1")
def sha256(s):                                raise HelperNotImplemented("sha256")
def hmac(algorithm, data, secret):            raise HelperNotImplemented("hmac")

# 인코딩
def hex_encode(s):                            raise HelperNotImplemented("hex_encode")

# 문자열
def to_upper(s):                              raise HelperNotImplemented("to_upper")
def trim(s, cutset=" "):                      raise HelperNotImplemented("trim")
def replace(s, old, new):                     raise HelperNotImplemented("replace")
def concat(*args):                            raise HelperNotImplemented("concat")
def repeat(s, count):                         raise HelperNotImplemented("repeat")
def padding(s, char, size):                   raise HelperNotImplemented("padding")
def to_number(s):                             raise HelperNotImplemented("to_number")

# 시간
def unix_time(offset=0):                      raise HelperNotImplemented("unix_time")

# 페이로드 생성기
def generate_jwt(*args):                      raise HelperNotImplemented("generate_jwt")
def generate_java_gadget(gadget, cmd, enc):   raise HelperNotImplemented("generate_java_gadget")


# ─────────────────────────────────────────────
# 등록표 ({{ }} 안에서 쓰는 이름 -> 함수)
# ─────────────────────────────────────────────
IMPLEMENTED = {
    "rand_base": rand_base,
    "rand_text_alpha": rand_text_alpha,
    "rand_text_numeric": rand_text_numeric,
    "rand_text_alphanumeric": rand_text_alphanumeric,
    "rand_int": rand_int,
    "to_lower": to_lower,
    "url_encode": url_encode,
    "url_decode": url_decode,
    "base64": base64,
    "base64_decode": base64_decode,
    "hex_decode": hex_decode,
    "date_time": date_time,
    # dsl 매처용
    "contains": contains,
    "contains_all": contains_all,
    "contains_any": contains_any,
    "regex": regex,
    "starts_with": starts_with,
    "ends_with": ends_with,
    "len": length,
}

NOT_IMPLEMENTED = {
    "md5": md5, "sha1": sha1, "sha256": sha256, "hmac": hmac,
    "hex_encode": hex_encode,
    "to_upper": to_upper, "trim": trim, "replace": replace, "concat": concat,
    "repeat": repeat, "padding": padding, "to_number": to_number,
    "unix_time": unix_time,
    "generate_jwt": generate_jwt, "generate_java_gadget": generate_java_gadget,
}

# 옛 이름(밑줄 없음) 별칭 ─ 실제 템플릿에 섞여 있음
ALIASES = {
    "randbase": "rand_base",
    "urlencode": "url_encode",
    "urldecode": "url_decode",
    "tolower": "to_lower",
    "toupper": "to_upper",
    "base64decode": "base64_decode",
    "hexdecode": "hex_decode",
    "hexencode": "hex_encode",
    "startswith": "starts_with",
    "endswith": "ends_with",
}

HELPERS = {**IMPLEMENTED, **NOT_IMPLEMENTED}
HELPERS.update({alias: HELPERS[real] for alias, real in ALIASES.items()})
