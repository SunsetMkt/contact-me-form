import os

import flask
import flask_cors
import requests

app = flask.Flask(__name__)


HCAPTCHA_SITE_KEY = os.environ.get("HCAPTCHA_SITE_KEY")
HCAPTCHA_SECRET_KEY = os.environ.get("HCAPTCHA_SECRET_KEY")
ENDPOINT_TOKEN = os.environ.get("ENDPOINT_TOKEN")


# CORS
# flask_cors.CORS(app, resources={r"/*": {"origins": "*"}})
# Allow *.lwd-temp.* and *.lwd-temp.*:port
flask_cors.CORS(app, resources={
                r"/*": {"origins": r"^(https?://)?(\w+\.)?(lwd-temp)\.?(\w+)?(:\d+)?$"}})


def post_message_to_endpoint(message, remote_ip='Unknown'):
    payload = {
        "to": "i@lwd-temp.top",
        "subject": "Contact Me Form from %s" % remote_ip,
        "body": message,
        "token": ENDPOINT_TOKEN,
        "html": 0
    }
    r = requests.post("https://noreply.lwd-temp.top/send", json=payload)
    r.raise_for_status()
    return r


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
        post_message_to_endpoint(message, remote_ip)
        return flask.render_template('success.html', message=message)
    else:
        if "error-codes" in response_json:
            message = "hCaptcha error: " + response_json["error-codes"][0]
        else:
            message = "hCaptcha error, have you solved the captcha?"
        return flask.render_template('deny.html', message=message)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
