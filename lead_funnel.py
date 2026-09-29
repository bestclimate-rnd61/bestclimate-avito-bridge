import html
import os
import re
import secrets
import time
from collections import defaultdict, deque
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

router = APIRouter()

BRAND_NAME = os.getenv("LEAD_BRAND_NAME", "Бест Климат Ростов")
TELEGRAM_BOT_TOKEN = os.getenv("LEAD_TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_CHAT_ID = os.getenv("LEAD_TELEGRAM_ADMIN_CHAT_ID", "")
TELEGRAM_CONTACT_URL = os.getenv("LEAD_TELEGRAM_CONTACT_URL", "https://t.me/BestClimateRostovBot").strip()
TELEGRAM_CHANNEL_URL = os.getenv("LEAD_TELEGRAM_CHANNEL_URL", "https://t.me/bestclimate_club").strip()
TELEGRAM_CHANNEL_CHAT = os.getenv("LEAD_TELEGRAM_CHANNEL_CHAT", "@bestclimate_club").strip()
TELEGRAM_WEBHOOK_SECRET = os.getenv("LEAD_TELEGRAM_WEBHOOK_SECRET", "")
REQUIRE_TELEGRAM_SUBSCRIPTION = os.getenv("LEAD_REQUIRE_TELEGRAM_SUBSCRIPTION", "false").lower() in {"1", "true", "yes", "on"}
WHATSAPP_PHONE = re.sub(r"\D+", "", os.getenv("LEAD_WHATSAPP_PHONE", ""))
MAX_CONTACT_URL = os.getenv("LEAD_MAX_CONTACT_URL", "").strip()
RELAY_URL = os.getenv("LEAD_RELAY_URL", "https://korziny.bestclimate-rnd.ru/send.php").strip()
PUBLIC_BASE_URL = os.getenv("LEAD_PUBLIC_BASE_URL", "").strip()

_RATE_WINDOW_SECONDS = 600
_RATE_MAX_REQUESTS = 8
_rate: dict[str, deque[float]] = defaultdict(deque)


class LeadInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=7, max_length=32)
    city: str = Field(default="", max_length=80)
    service: str = Field(min_length=2, max_length=120)
    messenger: str = Field(default="", max_length=40)
    source: str = Field(default="site", max_length=80)
    consent: bool
    marketing_consent: bool = False
    website: str = Field(default="", max_length=200)


def _clean_phone(value: str) -> str:
    cleaned = re.sub(r"[^0-9+]", "", value.strip())
    digits = re.sub(r"\D", "", cleaned)
    if len(digits) < 7 or len(digits) > 15:
        raise HTTPException(status_code=422, detail="Некорректный номер телефона")
    return cleaned[:20]


def _rate_limit(ip: str) -> None:
    now = time.time()
    q = _rate[ip]
    while q and q[0] < now - _RATE_WINDOW_SECONDS:
        q.popleft()
    if len(q) >= _RATE_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Слишком много заявок. Попробуйте позже.")
    q.append(now)


def _telegram_base_url() -> str:
    if not TELEGRAM_CONTACT_URL:
        return ""
    parts = urlsplit(TELEGRAM_CONTACT_URL)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _telegram_client_url(certificate_code: str) -> str:
    base = _telegram_base_url()
    if not base:
        return ""
    start = "cert_" + re.sub(r"[^A-Za-z0-9_-]", "", certificate_code)
    return f"{base}?start={start}"


def _base_url() -> str:
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL.rstrip("/")
    railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if railway_domain:
        if railway_domain.startswith("http://") or railway_domain.startswith("https://"):
            return railway_domain.rstrip("/")
        return f"https://{railway_domain}"
    return "https://bestclimate-avito-bridge-live-production.up.railway.app"


def _contact_links(certificate_code: str = "") -> dict[str, str]:
    telegram = _telegram_client_url(certificate_code) if certificate_code else TELEGRAM_CONTACT_URL
    return {
        "telegram": telegram,
        "channel": TELEGRAM_CHANNEL_URL,
        "whatsapp": f"https://wa.me/{WHATSAPP_PHONE}" if WHATSAPP_PHONE else "",
        "max": MAX_CONTACT_URL,
    }


async def _telegram_api(method: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not TELEGRAM_BOT_TOKEN:
        return None
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}", json=payload)
        if response.status_code >= 400:
            return None
        data = response.json()
        return data if isinstance(data, dict) else None
    except (httpx.HTTPError, ValueError):
        return None


async def _telegram_send(chat_id: int | str, text: str, reply_markup: dict[str, Any] | None = None) -> bool:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    data = await _telegram_api("sendMessage", payload)
    return bool(data and data.get("ok"))


async def _answer_callback(callback_query_id: str, text: str = "") -> None:
    payload: dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    await _telegram_api("answerCallbackQuery", payload)


async def _is_channel_member(user_id: int | str) -> bool | None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_CHAT:
        return None
    data = await _telegram_api("getChatMember", {"chat_id": TELEGRAM_CHANNEL_CHAT, "user_id": user_id})
    if not data or not data.get("ok") or not isinstance(data.get("result"), dict):
        return None
    member = data["result"]
    status = str(member.get("status", ""))
    if status in {"creator", "administrator", "member"}:
        return True
    if status == "restricted":
        return bool(member.get("is_member"))
    return False


def _activation_markup(certificate_code: str) -> dict[str, Any]:
    rows: list[list[dict[str, str]]] = []
    if TELEGRAM_CHANNEL_URL:
        rows.append([{"text": "🔥 Вступить в Бест Климат | Акции и выгода", "url": TELEGRAM_CHANNEL_URL}])
    rows.append([{"text": "✅ Я подписался — проверить", "callback_data": f"checkcert:{certificate_code}"}])
    return {"inline_keyboard": rows}


def _certificate_markup(certificate_code: str) -> dict[str, Any]:
    rows: list[list[dict[str, str]]] = [
        [{"text": "🎫 Открыть сертификат 3 000 ₽", "url": f"{_base_url()}/lead/certificate/{certificate_code}"}],
    ]
    if WHATSAPP_PHONE:
        rows.append([{"text": "💬 Написать менеджеру", "url": f"https://wa.me/{WHATSAPP_PHONE}"}])
    return {"inline_keyboard": rows}


async def _send_certificate(chat_id: int | str, certificate_code: str) -> bool:
    body = (
        "✅ <b>Подписка подтверждена!</b>\n\n"
        "🎁 Ваш подарочный сертификат на <b>3 000 ₽ активирован</b>.\n"
        f"Код: <code>{certificate_code}</code>\n\n"
        "Сохраните сообщение и покажите код менеджеру при оформлении заказа."
    )
    return await _telegram_send(chat_id, body, _certificate_markup(certificate_code))


@router.on_event("startup")
async def _setup_telegram_webhook() -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_WEBHOOK_SECRET:
        return
    webhook_url = f"{_base_url()}/telegram/webhook"
    await _telegram_api(
        "setWebhook",
        {
            "url": webhook_url,
            "secret_token": TELEGRAM_WEBHOOK_SECRET,
            "allowed_updates": ["message", "callback_query"],
            "drop_pending_updates": False,
        },
    )


async def _notify_telegram_direct(lead: LeadInput, phone: str, certificate_code: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ADMIN_CHAT_ID:
        return False
    text = (
        f"🔥 <b>Новая заявка — {html.escape(BRAND_NAME)}</b>\n\n"
        f"Имя: <b>{html.escape(lead.name.strip())}</b>\n"
        f"Телефон: <code>{html.escape(phone)}</code>\n"
        f"Город: {html.escape(lead.city.strip() or '—')}\n"
        f"Интерес: <b>{html.escape(lead.service.strip())}</b>\n"
        f"Мессенджер: {html.escape(lead.messenger.strip() or '—')}\n"
        f"Источник: {html.escape(lead.source.strip() or 'site')}\n"
        f"Сертификат: <code>{certificate_code}</code>\n"
        f"Активация через Telegram-клуб: {'да' if REQUIRE_TELEGRAM_SUBSCRIPTION else 'нет'}\n"
        f"Рекламные сообщения: {'да' if lead.marketing_consent else 'нет'}"
    )
    return await _telegram_send(TELEGRAM_ADMIN_CHAT_ID, text)


async def _relay_admin(lead: LeadInput, phone: str, certificate_code: str) -> dict[str, Any]:
    result: dict[str, Any] = {"reachable": False, "ok": False, "telegram_sent": False, "email_accepted": False}
    if not RELAY_URL:
        return result
    payload = {
        "website": "",
        "consent": "1",
        "product": lead.service.strip(),
        "qty": "1",
        "size": "",
        "ral": "",
        "city": lead.city.strip(),
        "install": f"Предпочтительный канал: {lead.messenger.strip() or 'не указан'}",
        "contact": f"{lead.name.strip()} — {phone}",
        "comment": (
            f"Источник: {lead.source.strip() or 'site'}\n"
            f"Сертификат: {certificate_code}\n"
            f"Статус сертификата: {'ожидает подписку в Telegram-клубе' if REQUIRE_TELEGRAM_SUBSCRIPTION else 'выдан'}\n"
            f"Согласие на акции: {'да' if lead.marketing_consent else 'нет'}"
        ),
    }
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.post(RELAY_URL, data=payload, headers={"User-Agent": "BestClimateLeadFunnel/3.0"})
        result["reachable"] = True
        try:
            data = response.json()
        except ValueError:
            data = {}
        result["status"] = response.status_code
        result["ok"] = bool(response.status_code < 400 and isinstance(data, dict) and data.get("ok"))
        if isinstance(data, dict):
            result["telegram_sent"] = bool(data.get("telegram_sent"))
            result["email_accepted"] = bool(data.get("email_accepted"))
            if data.get("request_id"):
                result["request_id"] = str(data.get("request_id"))[:64]
    except httpx.HTTPError:
        pass
    return result


async def _probe_relay() -> bool:
    if not RELAY_URL:
        return False
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            response = await client.post(
                RELAY_URL,
                data={"website": "healthcheck", "consent": "1"},
                headers={"User-Agent": "BestClimateLeadProbe/1.0"},
            )
        return response.status_code in {400, 403, 405, 413, 422, 429} or response.status_code < 400
    except httpx.HTTPError:
        return False


@router.post("/api/lead")
async def create_lead(payload: LeadInput, request: Request) -> dict[str, Any]:
    ip = request.client.host if request.client else "unknown"
    _rate_limit(ip)
    if payload.website:
        return {"ok": True, "notification_sent": False}
    if not payload.consent:
        raise HTTPException(status_code=422, detail="Нужно согласие на обработку персональных данных")

    phone = _clean_phone(payload.phone)
    certificate_code = "BC-" + secrets.token_hex(6).upper()
    relay = await _relay_admin(payload, phone, certificate_code)
    direct_telegram_sent = False
    if not relay.get("telegram_sent"):
        direct_telegram_sent = await _notify_telegram_direct(payload, phone, certificate_code)

    response: dict[str, Any] = {
        "ok": True,
        "notification_sent": bool(relay.get("telegram_sent") or direct_telegram_sent),
        "email_accepted": bool(relay.get("email_accepted")),
        "relay_ok": bool(relay.get("ok")),
        "activation_required": REQUIRE_TELEGRAM_SUBSCRIPTION,
        "contact_links": _contact_links(certificate_code),
    }
    if not REQUIRE_TELEGRAM_SUBSCRIPTION:
        response["certificate_code"] = certificate_code
        response["certificate_url"] = f"/lead/certificate/{certificate_code}"
    return response


@router.get("/lead/certificate/{certificate_code}", response_class=HTMLResponse)
async def certificate(certificate_code: str) -> HTMLResponse:
    if not re.fullmatch(r"BC-[A-F0-9]{12}", certificate_code):
        raise HTTPException(status_code=404, detail="Сертификат не найден")
    safe = html.escape(certificate_code)
    return HTMLResponse(f"""<!doctype html><html lang='ru'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Сертификат {safe}</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#101216;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;padding:24px}}.c{{max-width:720px;margin:6vh auto;background:linear-gradient(145deg,#fffdf6,#d9cfb7);color:#171717;border-radius:28px;padding:44px 28px;text-align:center;box-shadow:0 20px 70px #0007}}.brand{{font-weight:800;letter-spacing:.08em}}h1{{font-size:42px;margin:18px 0 4px}}.sum{{font-size:64px;font-weight:900}}.code{{font-size:24px;letter-spacing:.12em;font-weight:800;margin:28px 0}}button{{padding:14px 20px;border:0;border-radius:12px;font-size:16px;font-weight:700}}@media print{{button{{display:none}}body{{background:white;padding:0}}.c{{box-shadow:none;margin:0;max-width:none;min-height:100vh;display:flex;flex-direction:column;justify-content:center}}}}</style><body><div class='c'><div class='brand'>{html.escape(BRAND_NAME)}</div><h1>Подарочный сертификат</h1><div class='sum'>3 000 ₽</div><p>на покупку / монтаж климатического оборудования</p><div class='code'>{safe}</div><p>Покажите код менеджеру при оформлении заказа.</p><button onclick='window.print()'>Сохранить / распечатать</button></div></body></html>""")


@router.get("/lead/privacy", response_class=HTMLResponse)
async def privacy() -> HTMLResponse:
    return HTMLResponse("""<!doctype html><html lang='ru'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Обработка персональных данных</title><style>body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;max-width:760px;margin:40px auto;padding:0 20px;line-height:1.55;color:#171717}h1{font-size:28px}a{color:#0a67d1}</style><body><h1>Согласие на обработку персональных данных</h1><p>Отправляя форму, пользователь добровольно передаёт имя, номер телефона, город и информацию о выбранной услуге для обработки обращения, связи по заявке и предоставления запрошенного предложения или сертификата.</p><p>Согласие на рекламные сообщения запрашивается отдельно и не является обязательным условием отправки заявки.</p><p><a href='/lead'>Вернуться к форме</a></p></body></html>""")


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)) -> dict[str, bool]:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Telegram webhook is not configured")
    if not x_telegram_bot_api_secret_token or not secrets.compare_digest(x_telegram_bot_api_secret_token, TELEGRAM_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized")
    update = await request.json()
    if not isinstance(update, dict):
        return {"ok": True}

    callback = update.get("callback_query")
    if isinstance(callback, dict):
        callback_id = str(callback.get("id", ""))
        callback_data = str(callback.get("data", ""))
        from_user = callback.get("from") if isinstance(callback.get("from"), dict) else {}
        user_id = from_user.get("id")
        message = callback.get("message") if isinstance(callback.get("message"), dict) else {}
        chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
        chat_id = chat.get("id") or user_id
        if callback_data.startswith("checkcert:") and user_id and chat_id:
            certificate_code = callback_data.split(":", 1)[1]
            if re.fullmatch(r"BC-[A-F0-9]{12}", certificate_code):
                member = await _is_channel_member(user_id)
                if member is True:
                    await _answer_callback(callback_id, "Подписка подтверждена ✅")
                    await _send_certificate(chat_id, certificate_code)
                elif member is False:
                    await _answer_callback(callback_id, "Подписка пока не найдена. Вступите в канал и нажмите ещё раз.")
                else:
                    await _answer_callback(callback_id, "Не удалось проверить подписку. Попробуйте ещё раз через минуту.")
        return {"ok": True}

    message = update.get("message")
    if not isinstance(message, dict):
        return {"ok": True}
    chat = message.get("chat")
    text = message.get("text")
    if not isinstance(chat, dict) or not isinstance(chat.get("id"), (int, str)):
        return {"ok": True}
    chat_id = chat["id"]
    user = message.get("from") if isinstance(message.get("from"), dict) else {}
    user_id = user.get("id", chat_id)
    text = text if isinstance(text, str) else ""

    certificate_code = ""
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2 and parts[1].startswith("cert_"):
            candidate = parts[1][5:]
            if re.fullmatch(r"BC-[A-F0-9]{12}", candidate):
                certificate_code = candidate

    if certificate_code and REQUIRE_TELEGRAM_SUBSCRIPTION:
        member = await _is_channel_member(user_id)
        if member is True:
            await _send_certificate(chat_id, certificate_code)
        else:
            body = (
                "🎁 <b>Ваш сертификат на 3 000 ₽ зарезервирован.</b>\n\n"
                "Чтобы активировать его, вступите в наш клуб <b>«Бест Климат | Акции и выгода»</b>, "
                "где публикуем акции, скидки и специальные предложения.\n\n"
                "После вступления нажмите <b>«Я подписался — проверить»</b>."
            )
            await _telegram_send(chat_id, body, _activation_markup(certificate_code))
        return {"ok": True}

    if certificate_code:
        await _send_certificate(chat_id, certificate_code)
        return {"ok": True}

    body = f"Здравствуйте! Это {html.escape(BRAND_NAME)}. Здесь можно получать полезные материалы, акции и предложения по климатической технике."
    buttons: list[list[dict[str, str]]] = []
    if TELEGRAM_CHANNEL_URL:
        buttons.append([{"text": "🔥 Вступить в клуб", "url": TELEGRAM_CHANNEL_URL}])
    if WHATSAPP_PHONE:
        buttons.append([{"text": "Написать менеджеру в WhatsApp", "url": f"https://wa.me/{WHATSAPP_PHONE}"}])
    await _telegram_send(chat_id, body, {"inline_keyboard": buttons} if buttons else None)
    return {"ok": True}


@router.get("/lead", response_class=HTMLResponse)
async def lead_page() -> HTMLResponse:
    brand = html.escape(BRAND_NAME)
    return HTMLResponse(f"""<!doctype html><html lang='ru'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'><title>Подарочный сертификат — {brand}</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#0b0d10;color:#f5f7fa;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}.wrap{{max-width:680px;margin:0 auto;padding:24px 16px 48px}}.hero{{padding:28px 0 16px}}h1{{font-size:34px;line-height:1.03;margin:0 0 12px}}.sub{{color:#aeb6c2;font-size:17px;line-height:1.45}}.card{{background:#15191f;border:1px solid #272d36;border-radius:22px;padding:20px;box-shadow:0 14px 38px rgba(0,0,0,.26)}}label{{display:block;font-size:14px;color:#c8ced7;margin:15px 0 7px}}input,select{{width:100%;border:1px solid #343b46;background:#0e1217;color:#fff;border-radius:14px;padding:14px 15px;font-size:16px;outline:none}}input:focus,select:focus{{border-color:#7d96ff}}button{{width:100%;border:0;border-radius:14px;padding:15px 18px;margin-top:18px;font-size:17px;font-weight:700;background:#86a0ff;color:#0b1021}}.check{{display:flex;gap:10px;align-items:flex-start;margin-top:14px;color:#b8c0cb;font-size:13px;line-height:1.4}}.check input{{width:18px;height:18px;margin:1px 0 0;flex:0 0 18px}}.note{{font-size:12px;color:#7f8997;margin-top:12px}}.hidden{{display:none}}.certificate{{margin-top:18px;padding:22px;border-radius:20px;background:linear-gradient(145deg,#f5f2e8,#d7cfb8);color:#151515;text-align:center;border:1px solid #fff}}.certificate b{{font-size:28px}}.code{{font-size:22px;letter-spacing:2px;font-weight:800;margin:12px 0}}.links{{display:grid;gap:10px;margin-top:16px}}.links a{{display:block;text-align:center;text-decoration:none;padding:14px;border-radius:13px;background:#222832;color:#fff;font-weight:700}}.links a.primary{{background:#2aabee;color:#fff}}.links a.hot{{background:#7f5af0;color:#fff}}.err{{margin-top:12px;color:#ff9d9d}}a{{color:#9db1ff}}.hp{{position:absolute;left:-9999px;opacity:0}}.status{{font-size:14px;color:#c0c8d3;margin-top:14px;line-height:1.45}}</style></head><body><div class='wrap'><section class='hero'><h1>Получите сертификат на 3 000 ₽ 🎫</h1><div class='sub'>Оставьте заявку. Контакт сразу поступит менеджеру. Если включена клубная активация, сертификат активируется после подписки на Telegram-клуб.</div></section><div class='card'><form id='leadForm'><input class='hp' name='website' autocomplete='off' tabindex='-1'><label>Имя</label><input name='name' required minlength='2' maxlength='80' placeholder='Как к вам обращаться'><label>Телефон</label><input name='phone' required inputmode='tel' placeholder='+7 999 000-00-00'><label>Город</label><input name='city' maxlength='80' placeholder='Например, Ростов-на-Дону'><label>Что вас интересует</label><select name='service' required><option value=''>Выберите услугу</option><option>Кондиционер с установкой</option><option>Тепловой насос</option><option>Монтаж / закладка трассы</option><option>Ремонт / обслуживание</option><option>Вентиляция</option><option>Корзины / кронштейны / подставки</option><option>Другое</option></select><label>Где удобнее ответить</label><select name='messenger'><option>WhatsApp</option><option>Telegram</option><option>MAX</option><option>Звонок</option></select><label class='check'><input type='checkbox' name='consent' required><span>Согласен на обработку персональных данных для ответа на заявку. <a href='/lead/privacy' target='_blank'>Условия</a></span></label><label class='check'><input type='checkbox' name='marketing_consent'><span>Хочу получать акции и специальные предложения. Необязательно.</span></label><button type='submit'>Получить сертификат</button><div class='note'>Без спама. Рекламное согласие отдельно и по желанию.</div><div id='err' class='err'></div></form><div id='success' class='hidden'><div id='certificateBox' class='certificate hidden'><div>ПОДАРОЧНЫЙ СЕРТИФИКАТ</div><b>3 000 ₽</b><div>на покупку / монтаж климатического оборудования</div><div id='certCode' class='code'></div><div>{brand}</div></div><div id='status' class='status'></div><div class='links' id='contactLinks'></div><button type='button' onclick='location.reload()'>Новая заявка</button></div></div></div><script>const form=document.getElementById('leadForm'),err=document.getElementById('err'),success=document.getElementById('success');form.addEventListener('submit',async(e)=>{{e.preventDefault();err.textContent='';const fd=new FormData(form);const body={{name:fd.get('name'),phone:fd.get('phone'),city:fd.get('city')||'',service:fd.get('service'),messenger:fd.get('messenger')||'',source:new URLSearchParams(location.search).get('utm_source')||'instagram',consent:fd.get('consent')==='on',marketing_consent:fd.get('marketing_consent')==='on',website:fd.get('website')||''}};try{{const r=await fetch('/api/lead',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});const data=await r.json();if(!r.ok)throw new Error(data.detail||'Не удалось отправить заявку');const box=document.getElementById('contactLinks');box.innerHTML='';const make=(text,url,cls='')=>{{if(!url)return;const a=document.createElement('a');a.href=url;a.target='_blank';a.rel='noopener';a.textContent=text;if(cls)a.className=cls;box.appendChild(a)}};if(data.activation_required){{document.getElementById('status').innerHTML='✅ Заявка уже передана менеджеру.<br><br>🎁 Чтобы <b>активировать сертификат 3 000 ₽</b>, откройте Telegram, вступите в наш клуб и подтвердите подписку в боте.';make('📲 Активировать сертификат через Telegram',data.contact_links?.telegram,'primary');make('🔥 Открыть клуб «Бест Климат | Акции и выгода»',data.contact_links?.channel,'hot')}}else{{document.getElementById('certificateBox').classList.remove('hidden');document.getElementById('certCode').textContent=data.certificate_code||'';document.getElementById('status').textContent=data.email_accepted?'Заявка принята. Копия отправлена менеджеру на почту.':'Заявка принята. Менеджер получил уведомление.';make('Сохранить / распечатать сертификат',data.certificate_url);make('📲 Открыть Telegram',data.contact_links?.telegram,'primary')}}make('Написать в WhatsApp',data.contact_links?.whatsapp);make('Написать в MAX',data.contact_links?.max);form.classList.add('hidden');success.classList.remove('hidden');window.scrollTo({{top:0,behavior:'smooth'}})}}catch(ex){{err.textContent=ex.message||'Ошибка. Попробуйте ещё раз.'}}}});</script></body></html>""")


@router.get("/lead/health")
async def lead_health() -> dict[str, Any]:
    relay_reachable = await _probe_relay()
    membership_check_ready = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_CHAT)
    return {
        "ok": True,
        "service": "bestclimate-lead-funnel",
        "relay_reachable": relay_reachable,
        "telegram_bot_configured": bool(TELEGRAM_BOT_TOKEN),
        "telegram_admin_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_CHAT_ID),
        "telegram_webhook_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET),
        "telegram_membership_check_ready": membership_check_ready,
        "telegram_subscription_required": REQUIRE_TELEGRAM_SUBSCRIPTION,
        "contact_links": {key: bool(value) for key, value in _contact_links().items()},
    }
