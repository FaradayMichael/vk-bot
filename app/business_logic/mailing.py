from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jinja2 import (
    Environment as JinjaEnvironment
)

from app.utils.config import Config
from app.utils.smtp import (
    SMTP as SMTPConnection,
    send as send_mail
)


async def send_password(
        login: str,
        password: str,
        smtp: SMTPConnection,
        jinja: JinjaEnvironment,
        conf: Config
):
    await send_password_email(smtp, login, password, jinja, conf)


async def send_registration_email(
        smtp: SMTPConnection,
        email: str,
        code: int,
        jinja: JinjaEnvironment,
        conf: Config
):
    msg = MIMEMultipart()
    msg['To'] = email
    msg['From'] = conf.smtp.sender
    msg['Subject'] = 'Регистрация'

    part = MIMEText(await generate_register_template(jinja, code=code), 'html')

    msg.attach(part)

    await send_mail(
        smtp,
        msg
    )


async def send_recover_email(
        smtp: SMTPConnection,
        email: str,
        code: int,
        jinja: JinjaEnvironment,
        conf: Config
):
    msg = MIMEMultipart()
    msg['To'] = email
    msg['From'] = conf.smtp.sender
    msg['Subject'] = 'Восстановление пароля'

    part = MIMEText(await generate_recover_template(jinja, code=code), 'html')

    msg.attach(part)

    await send_mail(
        smtp,
        msg
    )


async def send_password_email(
        smtp: SMTPConnection,
        email: str,
        password: str,
        jinja: JinjaEnvironment,
        conf: Config
):
    msg = MIMEMultipart()
    msg['To'] = email
    msg['From'] = conf.smtp.sender
    msg['Subject'] = 'Пароль для входа'

    part = MIMEText(await generate_password_template(jinja, email=email, password=password), 'html')

    msg.attach(part)

    await send_mail(
        smtp,
        msg
    )


async def send_change_email(
        smtp: SMTPConnection,
        email: str,
        code: int,
        jinja: JinjaEnvironment,
        conf: Config
):
    msg = MIMEMultipart()
    msg['To'] = email
    msg['From'] = conf.smtp.sender
    msg['Subject'] = 'Изменен email'

    part = MIMEText(await generate_change_template_email(jinja, code=code), 'html')

    msg.attach(part)

    await send_mail(
        smtp,
        msg
    )


async def generate_register_template(jinja, **data) -> str:
    return await generate_tpl(jinja, "mail/auth/confirm-message.html", **data)


async def generate_recover_template(jinja, **data) -> str:
    return await generate_tpl(jinja, "mail/auth/recover-password.html", **data)


async def generate_password_template(jinja, **data) -> str:
    return await generate_tpl(jinja, "mail/auth/send-password.html", **data)


async def generate_register_template_phone(jinja, **data) -> str:
    return await generate_tpl(jinja, "mail/auth/confirm-message-phone.txt", **data)


async def generate_recover_template_phone(jinja, **data) -> str:
    return await generate_tpl(jinja, "mail/auth/recover-password-phone.txt", **data)


async def generate_password_template_phone(jinja, **data) -> str:
    return await generate_tpl(jinja, "mail/auth/send-password-phone.txt", **data)


async def generate_change_template_email(jinja, **data) -> str:
    return await generate_tpl(jinja, "mail/auth/change-email.html", **data)


async def generate_tpl(jinja: JinjaEnvironment, path: str, **data) -> str:
    template = jinja.get_template(path)
    return template.render(**data)


def confirm_key(credentials: str) -> str:
    return f'confirm_{credentials}'
