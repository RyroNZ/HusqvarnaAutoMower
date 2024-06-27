from flask import Flask, render_template, jsonify
import threading
from mower_control import MowerControl

app = Flask(__name__)

mower_control = MowerControl()

@app.route('/')
def index():
    return render_template('index.html', status=mower_control.get_status())

if __name__ == '__main__':
    def run_scheduler():
        mower_control.run_scheduler()

    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()

    app.run(port=5000, host="0.0.0.0")