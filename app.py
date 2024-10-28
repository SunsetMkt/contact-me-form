import json
import os
import smtplib
from email.header import Header
from email.mime.text import MIMEText

import flask
import requests

app = flask.Flask(__name__)

# hCaptcha
HCAPTCHA_SITE_KEY = os.environ.get("HCAPTCHA_SITE_KEY")
HCAPTCHA_SECRET_KEY = os.environ.get("HCAPTCHA_SECRET_KEY")

# 邮件服务器
endpoint = os.environ.get("MAIL_ENDPOINT")
# 收件人
receiver = os.environ.get("MAIL_RECEIVER")


def get_ip():
    # Get IP
    # From headers first
    # cf-connecting-ip x-real-ip
    # x-forwarded-for
    # Then from request
    ip = flask.request.headers.get("cf-connecting-ip")
    if ip is None:
        ip = flask.request.headers.get("x-real-ip")
    if ip is None:
        ip = flask.request.headers.get("x-forwarded-for")
    if ip is None:
        ip = flask.request.remote_addr
    return ip


def get_request_info():
    method = flask.request.method
    headers = flask.request.headers.items()
    real_headers = {}
    for key, value in headers:
        real_headers[key] = value
    path = flask.request.path
    url = flask.request.url
    info = {
        "method": method,
        "headers": real_headers,
        "path": path,
        "url": url,
    }
    # To string
    info_str = json.dumps(info)
    return info_str


def NoneTypeHandler(obj):
    if obj is None:
        return ""
    else:
        return obj


def post_message_to_endpoint(message, remote_ip="Unknown", info="", frontendappend=""):
    # Append IP and useragent to message
    message += "\n\nIP: " + NoneTypeHandler(remote_ip)
    message += "\nRequestInfo: " + NoneTypeHandler(info)
    message += "\nFrontendAppend: " + NoneTypeHandler(frontendappend)

    try:
        payload = {
            "to": receiver,
            "subject": f"Contact Me Form from {remote_ip}",
            "body": message,
            "html": "0",
        }
        headers = {"content-type": "application/json"}

        response = requests.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()

        return True
    except Exception as e:
        return False


# Handle / (index)
@app.route("/", methods=["GET"])
def index():
    # return template('form.html')
    return flask.render_template("form.html", site_key=HCAPTCHA_SITE_KEY)


# Handle /submit
@app.route("/submit", methods=["POST"])
def submit_endpoint():
    # Get form data
    data = flask.request.form
    message = data.get("message")
    frontendappend = data.get("frontendappend")

    remote_ip = NoneTypeHandler(get_ip())

    # Get request info
    info = get_request_info()

    # Verify
    response = data.get("h-captcha-response")
    VERIFY_URL = "https://hcaptcha.com/siteverify"
    r = requests.post(
        VERIFY_URL,
        data={
            "secret": HCAPTCHA_SECRET_KEY,
            "response": response,
            "remoteip": remote_ip,
            "sitekey": HCAPTCHA_SITE_KEY,
        },
    )
    response_json = r.json()
    success = response_json["success"]
    try:
        if success:
            if post_message_to_endpoint(message, remote_ip, info, frontendappend):
                return flask.render_template("success.html", message=message)
            else:
                message = "It appears there might be an issue on our end. We apologize for the inconvenience."
                return flask.render_template("deny.html", message=message)
        else:
            if "error-codes" in response_json:
                message = (
                    "We've encountered an hCaptcha error: "
                    + response_json["error-codes"][0]
                )
            else:
                message = "We've encountered an hCaptcha error. Kindly ensure that you have successfully solved the captcha before proceeding."
            return flask.render_template("deny.html", message=message)
    except:
        message = "It appears there might be an issue on our end. We apologize for the inconvenience."
        return flask.render_template("deny.html", message=message)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
