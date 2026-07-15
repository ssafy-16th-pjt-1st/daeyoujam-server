from dataclasses import dataclass
import re
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgsk_[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)\b(openai_api_key|groq_api_key|database_url|jwt_secret)\b\s*[:=]\s*[^\s,;]+"),
]

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)\b(ignore|forget|bypass|override)\b.{0,40}\b(instruction|prompt|policy|rule|system|developer)\b"),
    re.compile(r"(?i)\b(system|developer)\s*(prompt|message|instruction)\b"),
    re.compile(r"(?i)\b(reveal|show|print|dump|leak|expose)\b.{0,40}\b(prompt|instruction|policy|secret|token|api[_-]?key|env)\b"),
    re.compile(r"(?i)\b(jailbreak|do anything now|dan mode|roleplay as)\b"),
    re.compile(r"(?i)\b(base64|rot13|hex)\b.{0,40}\b(prompt|secret|token|api[_-]?key)\b"),
    re.compile(r"(이전|위|앞선|기존).{0,12}(지시|규칙|프롬프트).{0,12}(무시|잊어|버려|따르지)"),
    re.compile(r"(시스템|개발자).{0,8}(프롬프트|메시지|지시).{0,12}(보여|출력|공개|알려)"),
    re.compile(r"(비밀|시크릿|토큰|API\s*키|환경변수|env).{0,12}(보여|출력|공개|알려|유출)"),
]

INTERNAL_INFO_PATTERNS = [
    re.compile(r"(?i)^\s*\.?env\s*$"),
    re.compile(r"(?i)\b(\.env|env file|environment variable|database_url|connection string)\b"),
    re.compile(r"(?i)\b(db|database|schema|table|server|backend|admin|credential|config)\b.{0,20}\b(info|detail|url|host|password|secret)\b"),
    re.compile(r"(db|DB|디비|데이터베이스).{0,12}(정보|접속|주소|url|URL|비번|비밀번호|계정|구조|스키마|테이블).{0,12}(알려|보여|출력|공개)?"),
    re.compile(r"(서버|백엔드|관리자|어드민).{0,12}(정보|주소|설정|계정|비밀번호|토큰|키).{0,12}(알려|보여|출력|공개)?"),
    re.compile(r"(환경변수|env|시크릿|비밀|토큰|API\s*키).{0,12}(알려|보여|출력|공개|뭐야)?"),
]

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass
class PromptSafety:
    blocked: bool
    reason: str | None = None


def redact_secrets(text: str) -> str:
    redacted = text or ""
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def sanitize_user_text(text: str, *, max_length: int = 500) -> str:
    cleaned = CONTROL_CHARS.sub(" ", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = redact_secrets(cleaned)
    return cleaned[:max_length]


def sanitize_user_profile(profile: dict[str, Any]) -> dict:
    if not isinstance(profile, dict):
        return {}

    nickname = sanitize_user_text(str(profile.get("nickname") or ""), max_length=30)
    district = sanitize_user_text(str(profile.get("district") or ""), max_length=20)
    interests = profile.get("interests") or []
    if not isinstance(interests, list):
        interests = []

    return {
        "nickname": nickname,
        "district": district,
        "interests": [sanitize_user_text(str(item), max_length=20) for item in interests[:8] if item],
    }


def assess_prompt_safety(message: str) -> PromptSafety:
    normalized = sanitize_user_text(message).lower()
    for pattern in INTERNAL_INFO_PATTERNS:
        if pattern.search(normalized):
            return PromptSafety(blocked=True, reason="internal_info")
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(normalized):
            return PromptSafety(blocked=True, reason="prompt_injection")
    return PromptSafety(blocked=False)


def blocked_prompt_answer(reason: str | None) -> str:
    if reason == "internal_info":
        return (
            "그 정보는 보안상 제공할 수 없어요. "
            ".env, DB 접속 정보, 서버 설정, API 키 같은 내부 정보는 공개 대상이 아닙니다. "
            "대전 장소 추천이나 여행 정보에 대해 물어봐 주세요."
        )
    return (
        "요청 안에 내부 지시나 비밀 정보를 우회하려는 내용이 포함되어 답변할 수 없어요. "
        "대전 장소나 여행 추천에 대해 다시 물어봐 주세요."
    )


def contains_sensitive_output(text: str) -> bool:
    if not text:
        return False
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        return True
    sensitive_terms = [
        "system prompt",
        "developer message",
        "api key",
        "OPENAI_API_KEY",
        "GROQ_API_KEY",
        "DATABASE_URL",
        "환경변수",
        "시스템 프롬프트",
        "개발자 메시지",
    ]
    lowered = text.lower()
    return any(term.lower() in lowered for term in sensitive_terms)
