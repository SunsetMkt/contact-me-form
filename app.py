import os
import smtplib
from email.header import Header
from email.mime.text import MIMEText

import flask
import flask_cors
import requests

app = flask.Flask(__name__)

# hCaptcha
HCAPTCHA_SITE_KEY = os.environ.get("HCAPTCHA_SITE_KEY")
HCAPTCHA_SECRET_KEY = os.environ.get("HCAPTCHA_SECRET_KEY")
# Yandex邮箱smtp服务器
host_server = 'smtp.yandex.com'
# Yandex邮箱smtp服务器端口
ssl_port = '465'
# 用户名
user = os.environ.get('YANDEX_MAIL_USER')
# 密码（应用密码，相当于token）
pwd = os.environ.get('YANDEX_MAIL_PWD')
# 发件人的邮箱
sender_mail = os.environ.get('YANDEX_MAIL_USER')
# 收件人
receiver = os.environ.get('MAIL_RECEIVER')


# CORS
# flask_cors.CORS(app, resources={r"/*": {"origins": "*"}})
# Allow *.lwd-temp.* and *.lwd-temp.*:port
flask_cors.CORS(app, resources={
                r"/*": {"origins": r"^(https?://)?(\w+\.)?(lwd-temp)\.?(\w+)?(:\d+)?$"}})


def post_message_to_endpoint(message, remote_ip='Unknown', ua='Unknown'):
    # Append IP and useragent to message
    message += "\n\nIP: " + remote_ip
    message += "\nUser-Agent: " + ua

    msg = MIMEText(message, "plain", 'utf-8')
    msg["Subject"] = Header(f"Contact Me Form from {remote_ip}", 'utf-8')
    msg["From"] = sender_mail
    msg["To"] = receiver
    try:
        # ssl登录
        smtp = smtplib.SMTP_SSL(host_server, ssl_port)
        smtp.ehlo(host_server)
        smtp.login(user, pwd)
        smtp.sendmail(sender_mail, receiver, msg.as_string())
        smtp.quit()
        return True
    except Exception as e:
        return False


# Handle / (index)
@app.route('/', methods=["GET"])
def index():
    # return template('form.html')
    return flask.render_template('form.html', site_key=HCAPTCHA_SITE_KEY)


# Handle /success
@app.route('/success', methods=["POST"])
def success():
    # Get form data
    data = flask.request.form
    message = data.get('message')

    # Get user ip
    # check cf-connecting-ip
    if "cf-connecting-ip" in flask.request.headers:
        remote_ip = flask.request.headers["cf-connecting-ip"]
    else:
        remote_ip = flask.request.remote_addr

    # Get useragent
    if "user-agent" in flask.request.headers:
        ua = flask.request.headers["user-agent"]
    else:
        ua = "Unknown"

    # Verify
    response = data.get('h-captcha-response')
    VERIFY_URL = "https://hcaptcha.com/siteverify"
    r = requests.post(VERIFY_URL, data={
        "secret": HCAPTCHA_SECRET_KEY,
        "response": response,
        "remoteip": remote_ip,
        "sitekey": HCAPTCHA_SITE_KEY
    })
    response_json = r.json()
    success = response_json["success"]
    if success:
        if post_message_to_endpoint(message, remote_ip, ua):
            return flask.render_template('success.html', message=message)
        else:
            message = "There's something wrong on our side."
            return flask.render_template('deny.html', message=message)
    else:
        if "error-codes" in response_json:
            message = "hCaptcha error: " + response_json["error-codes"][0]
        else:
            message = "hCaptcha error, have you solved the captcha?"
        return flask.render_template('deny.html', message=message)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
