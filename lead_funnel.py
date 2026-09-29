import html
import os
import re
import secrets
import time
from collections import defaultdict, deque
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

router = APIRouter()

BRAND_NAME = os.getenv("LEAD_BRAND_NAME", "Бест Климат Ростов")
TELEGRAM_BOT_TOKEN = os.getenv("LEAD_TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_CHAT_ID = os.getenv("LEAD_TELEGRAM_ADMIN_CHAT_ID", "")
WHATSAPP_PHONE = re.sub(r"\D+", "", os.getenv("LEAD_WHATSAPP_PHONE", ""))
TELEGRAM_CONTACT_URL = os.getenv("LEAD_TELEGRAM_CONTACT_URL", "")
MAX_CONTACT_URL = os.getenv("LEAD_MAX_CONTACT_URL", "")

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
    website: str = Field(default="", max_length=200)  # honeypot


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


async def _notify_telegram(lead: LeadInput, phone: str, certificate_code: str) -> bool:
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
        f"Рекламные сообщения: {'да' if lead.marketing_consent else 'нет'}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(
                url,
                json={
                    "chat_id": TELEGRAM_ADMIN_CHAT_ID,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
        return response.status_code < 400
    except httpx.HTTPError:
        return False


def _contact_links() -> dict[str, str]:
    return {
        "whatsapp": f"https://wa.me/{WHATSAPP_PHONE}" if WHATSAPP_PHONE else "",
        "telegram": TELEGRAM_CONTACT_URL,
        "max": MAX_CONTACT_URL,
    }


@router.post("/api/lead")
async def create_lead(payload: LeadInput, request: Request) -> dict[str, Any]:
    ip = request.client.host if request.client else "unknown"
    _rate_limit(ip)

    if payload.website:
        return {"ok": True, "certificate_code": "BC-OK", "notification_sent": False}
    if not payload.consent:
        raise HTTPException(status_code=422, detail="Нужно согласие на обработку персональных данных")

    phone = _clean_phone(payload.phone)
    certificate_code = "BC-" + secrets.token_hex(3).upper()
    notification_sent = await _notify_telegram(payload, phone, certificate_code)

    return {
        "ok": True,
        "certificate_code": certificate_code,
        "notification_sent": notification_sent,
        "contact_links": _contact_links(),
    }


@router.get("/lead/privacy", response_class=HTMLResponse)
async def privacy() -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html><html lang='ru'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
        <title>Обработка персональных данных</title>
        <style>body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;max-width:760px;margin:40px auto;padding:0 20px;line-height:1.55;color:#171717}h1{font-size:28px}a{color:#0a67d1}</style>
        <body><h1>Согласие на обработку персональных данных</h1>
        <p>Отправляя форму, пользователь добровольно передаёт имя, номер телефона, город и информацию о выбранной услуге для обработки обращения, связи по заявке и предоставления запрошенного предложения или сертификата.</p>
        <p>Согласие на рекламные сообщения запрашивается отдельно и не является обязательным условием отправки заявки.</p>
        <p>Для публикации полноценной политики конфиденциальности необходимо дополнить эту страницу реквизитами оператора, сроками хранения, порядком отзыва согласия и фактически используемыми подрядчиками/сервисами.</p>
        <p><a href='/lead'>Вернуться к форме</a></p></body></html>"""
    )


@router.get("/lead", response_class=HTMLResponse)
async def lead_page() -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang='ru'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>
<title>Подарочный сертификат — {html.escape(BRAND_NAME)}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#0b0d10;color:#f5f7fa;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
.wrap{{max-width:680px;margin:0 auto;padding:24px 16px 48px}}.hero{{padding:28px 0 16px}}h1{{font-size:34px;line-height:1.03;margin:0 0 12px}}.sub{{color:#aeb6c2;font-size:17px;line-height:1.45}}
.card{{background:#15191f;border:1px solid #272d36;border-radius:22px;padding:20px;box-shadow:0 14px 38px rgba(0,0,0,.26)}}label{{display:block;font-size:14px;color:#c8ced7;margin:15px 0 7px}}
input,select{{width:100%;border:1px solid #343b46;background:#0e1217;color:#fff;border-radius:14px;padding:14px 15px;font-size:16px;outline:none}}input:focus,select:focus{{border-color:#7d96ff}}
button{{width:100%;border:0;border-radius:14px;padding:15px 18px;margin-top:18px;font-size:17px;font-weight:700;background:#86a0ff;color:#0b1021}}
.check{{display:flex;gap:10px;align-items:flex-start;margin-top:14px;color:#b8c0cb;font-size:13px;line-height:1.4}}.check input{{width:18px;height:18px;margin:1px 0 0;flex:0 0 18px}}
.note{{font-size:12px;color:#7f8997;margin-top:12px}}.hidden{{display:none}}.certificate{{margin-top:18px;padding:22px;border-radius:20px;background:linear-gradient(145deg,#f5f2e8,#d7cfb8);color:#151515;text-align:center;border:1px solid #fff}}
.certificate b{{font-size:24px}}.code{{font-size:22px;letter-spacing:2px;font-weight:800;margin:12px 0}}.links{{display:grid;gap:10px;margin-top:16px}}.links a{{display:block;text-align:center;text-decoration:none;padding:14px;border-radius:13px;background:#222832;color:#fff}}
.err{{margin-top:12px;color:#ff9d9d}}a{{color:#9db1ff}}.hp{{position:absolute;left:-9999px;opacity:0}}
</style>
</head>
<body><div class='wrap'>
<section class='hero'><h1>Получите сертификат на 1 000 ₽ 🎫</h1><div class='sub'>Оставьте заявку — сертификат закрепится за вами, а менеджер свяжется по выбранной услуге.</div></section>
<div class='card'>
<form id='leadForm'>
<input class='hp' name='website' autocomplete='off' tabindex='-1'>
<label>Имя</label><input name='name' required minlength='2' maxlength='80' placeholder='Как к вам обращаться'>
<label>Телефон</label><input name='phone' required inputmode='tel' placeholder='+7 999 000-00-00'>
<label>Город</label><input name='city' maxlength='80' placeholder='Например, Ростов-на-Дону'>
<label>Что вас интересует</label>
<select name='service' required><option value=''>Выберите услугу</option><option>Кондиционер с установкой</option><option>Тепловой насос</option><option>Монтаж / закладка трассы</option><option>Ремонт / обслуживание</option><option>Вентиляция</option><option>Корзины / кронштейны / подставки</option><option>Другое</option></select>
<label>Где удобнее ответить</label><select name='messenger'><option>WhatsApp</option><option>Telegram</option><option>MAX</option><option>Звонок</option></select>
<label class='check'><input type='checkbox' name='consent' required><span>Согласен на обработку персональных данных для ответа на заявку. <a href='/lead/privacy' target='_blank'>Условия</a></span></label>
<label class='check'><input type='checkbox' name='marketing_consent'><span>Хочу получать акции и специальные предложения. Необязательно.</span></label>
<button type='submit'>Получить сертификат</button><div class='note'>Без спама. Рекламное согласие отдельно и по желанию.</div><div id='err' class='err'></div>
</form>
<div id='success' class='hidden'><div class='certificate'><div>ПОДАРОЧНЫЙ СЕРТИФИКАТ</div><b>1 000 ₽</b><div>на покупку / монтаж климатического оборудования</div><div id='certCode' class='code'></div><div>{html.escape(BRAND_NAME)}</div></div><div class='links' id='contactLinks'></div><button type='button' onclick='location.reload()'>Новая заявка</button></div>
</div></div>
<script>
const form=document.getElementById('leadForm'), err=document.getElementById('err'), success=document.getElementById('success');
form.addEventListener('submit', async (e)=>{{e.preventDefault();err.textContent='';const fd=new FormData(form);const body={{name:fd.get('name'),phone:fd.get('phone'),city:fd.get('city')||'',service:fd.get('service'),messenger:fd.get('messenger')||'',source:new URLSearchParams(location.search).get('utm_source')||'site',consent:fd.get('consent')==='on',marketing_consent:fd.get('marketing_consent')==='on',website:fd.get('website')||''}};try{{const r=await fetch('/api/lead',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});const data=await r.json();if(!r.ok)throw new Error(data.detail||'Не удалось отправить заявку');document.getElementById('certCode').textContent=data.certificate_code;const box=document.getElementById('contactLinks');box.innerHTML='';const labels={{whatsapp:'Написать в WhatsApp',telegram:'Написать в Telegram',max:'Написать в MAX'}};for(const [k,u] of Object.entries(data.contact_links||{{}})){{if(u){{const a=document.createElement('a');a.href=u;a.target='_blank';a.rel='noopener';a.textContent=labels[k]||k;box.appendChild(a)}}}}form.classList.add('hidden');success.classList.remove('hidden');window.scrollTo({{top:0,behavior:'smooth'}})}}catch(ex){{err.textContent=ex.message||'Ошибка. Попробуйте ещё раз.'}}}});
</script></body></html>"""
    )


@router.get("/lead/health")
async def lead_health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "bestclimate-lead-funnel",
        "telegram_notifications_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_CHAT_ID),
        "contact_links": {key: bool(value) for key, value in _contact_links().items()},
    }
