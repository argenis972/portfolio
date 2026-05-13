"""
Contact controller.

Endpoint:
  POST /api/contact
"""

from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.use_cases.send_contact import SendContactUseCase
from app.controllers.dependencies import get_send_contact_use_case
from app.core.contact_guard import ContactGuard, email_domain
from app.core.exceptions import DuplicateContactError
from app.core.idempotency import store, verify_idempotency
from app.schemas.contact import ContactRequest, ContactResponse

logger = structlog.get_logger(__name__)

_guard = ContactGuard()

router = APIRouter(tags=["Contact"])


async def _process_background_delivery(
    send_contact_uc: SendContactUseCase,
    request_data: ContactRequest,
    is_suspicious: bool,
    spam_score: int,
) -> None:
    """Executes contact delivery in the background, logging structured events."""
    try:
        success = await send_contact_uc.execute(
            name=request_data.name,
            email=request_data.email,
            subject=request_data.subject or "",
            message=request_data.message,
            is_suspicious=is_suspicious,
            spam_score=spam_score,
        )

        if success:
            logger.info(
                "contact_delivered",
                is_suspicious=is_suspicious,
                email_domain=email_domain(request_data.email),
                delivery_mode="background",
            )
        else:
            logger.error(
                "contact_delivery_failed",
                is_suspicious=is_suspicious,
                event_type="delivery_error",
                email_domain=email_domain(request_data.email),
                delivery_mode="background",
            )
    except Exception as e:
        logger.error(
            "contact_delivery_crash",
            error=str(e),
            event_type="system_error",
            email_domain=email_domain(request_data.email),
            delivery_mode="background",
        )


@router.post(
    "/contact",
    response_model=ContactResponse,
    summary="Send contact message",
    description="Submits a contact form message via Formspree in background. Rate limited to 10 messages/day per email.",
    responses={
        200: {"description": "Message queued successfully"},
        429: {"description": "Too many requests - rate limit exceeded"},
        400: {"description": "Duplicate content"},
    },
)
async def send_contact(
    request: Request,
    contact_request: ContactRequest,
    background_tasks: BackgroundTasks,
    send_contact_uc: Annotated[
        SendContactUseCase,
        Depends(get_send_contact_use_case),
    ],
    idempotency_key: Annotated[Optional[str], Depends(verify_idempotency)] = None,
) -> ContactResponse:
    cacheable_response: ContactResponse | None = None
    content_hash: str | None = None
    dedup_reserved = False
    email_adapter = getattr(send_contact_uc, "email_adapter", None)
    downstream = (
        getattr(email_adapter, "__class__", type("Adapter", (), {}))
        .__name__.replace("EmailAdapter", "")
        .lower()
        or "email_adapter"
    )

    try:
        # ── 1. Honeypot check ───────────────────────────────────────────────
        if _guard.check_honeypot(contact_request):
            logger.info(
                "contact_blocked",
                classification="HONEYPOT",
                action="silent_drop",
                event_type="security_event",
            )
            cacheable_response = ContactResponse(
                success=True,
                message="Message sent successfully! I will get back to you soon.",
                queue_status="accepted",
                delivery_mode="silent_drop",
                downstream="honeypot_guard",
            )
            return cacheable_response

        # ── 2. Spam score ───────────────────────────────────────────────────
        spam_score = _guard.get_spam_score(
            contact_request.message,
            contact_request.email,
            name=contact_request.name,
            subject=contact_request.subject or "",
        )

        if spam_score >= ContactGuard.SCORE_SILENT_DROP:
            logger.info(
                "contact_classified",
                classification="SILENT_SPAM",
                action="silent_drop",
                event_type="security_event",
                spam_score=spam_score,
                email_domain=email_domain(contact_request.email),
            )
            cacheable_response = ContactResponse(
                success=True,
                message="Message sent successfully! I will get back to you soon.",
                queue_status="accepted",
                delivery_mode="silent_drop",
                downstream="spam_guard",
            )
            return cacheable_response

        # ── 3. Content deduplication ────────────────────────────────────────
        content_hash = _guard.build_content_hash(
            contact_request.email, contact_request.message
        )
        dedup_reserved = await _guard.reserve_dedup(content_hash)

        if not dedup_reserved:
            logger.info(
                "duplicate_content_detected",
                event_type="security_event",
                content_hash_prefix=content_hash[:12],
                email_domain=email_domain(contact_request.email),
                context="shared_dedup_store",
            )
            raise DuplicateContactError()

        # ── 4. Rate limiting ────────────────────────────────────────────────
        # Set identity on request state so the limiter uses email as the key
        request.state.identity = f"email:{contact_request.email.lower().strip()}"
        _guard.apply_rate_limits(request)

        # ── 5. Classification logging ───────────────────────────────────────
        is_suspicious = spam_score > ContactGuard.SCORE_SUSPICIOUS
        logger.info(
            "contact_classified",
            classification="SUSPECT" if is_suspicious else "NORMAL",
            action="deliver_with_flag" if is_suspicious else "deliver",
            spam_score=spam_score,
            email_domain=email_domain(contact_request.email),
        )

        # ── 6. Delivery (Background Tasks) ──────────────────────────────────
        background_tasks.add_task(
            _process_background_delivery,
            send_contact_uc,
            contact_request,
            is_suspicious,
            spam_score,
        )

        logger.info(
            "contact_queued",
            is_suspicious=is_suspicious,
            email_domain=email_domain(contact_request.email),
        )

        cacheable_response = ContactResponse(
            success=True,
            message="Message sent successfully! I will get back to you soon.",
            queue_status="queued",
            delivery_mode="background",
            downstream=downstream,
        )
        return cacheable_response

    finally:
        # Since it's background processed and always success to user,
        # we don't release dedup_reserved (unless it crashed before enqueueing
        # and cacheable_response is None).
        if dedup_reserved and content_hash and cacheable_response is None:
            await _guard.release_dedup(content_hash)

        # Persist idempotency result
        if idempotency_key:
            if cacheable_response is not None:
                await store.set(idempotency_key, 200, cacheable_response.model_dump())
            else:
                await store.release(idempotency_key)
