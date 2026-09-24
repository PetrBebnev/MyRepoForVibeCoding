import os
from flask import Flask, render_template, session, jsonify, request

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')

QUESTIONS = [
    {"correct": 0},  # HTML
    {"correct": 2},  # <link>
    {"correct": 2},  # ===
    {"correct": 1},  # flex-контейнер
    {"correct": 0},  # push()
]

OPTIONS_COUNT = 4


def get_state():
    return {
        "currentIndex": session.get("currentIndex", 0),
        "score": session.get("score", 0),
        "answered": session.get("answered", []),
    }


def save_state(state):
    session["currentIndex"] = state["currentIndex"]
    session["score"] = state["score"]
    session["answered"] = state["answered"]


@app.route('/')
def index():
    state = get_state()
    return render_template('index.html', state=state, total_questions=len(QUESTIONS))


@app.route('/api/answer', methods=['POST'])
def answer():
    data = request.get_json(silent=True) or {}
    chosen = data.get('chosenIndex')

    state = get_state()
    index = state["currentIndex"]

    if index >= len(QUESTIONS):
        return jsonify({"error": "quiz finished"}), 400

    # bool — подкласс int, поэтому проверяем его ПЕРВЫМ
    if isinstance(chosen, bool) or not isinstance(chosen, int):
        return jsonify({"error": "chosenIndex must be int"}), 400
    if not (0 <= chosen < OPTIONS_COUNT):
        return jsonify({"error": "chosenIndex out of range"}), 400

    if index in state["answered"]:
        return jsonify(state)

    if QUESTIONS[index]["correct"] == chosen:
        state["score"] += 1

    state["answered"].append(index)
    save_state(state)
    return jsonify(state)


@app.route('/api/next', methods=['POST'])
def next_question():
    state = get_state()
    if state["currentIndex"] < len(QUESTIONS):
        state["currentIndex"] += 1
        save_state(state)
    return jsonify(state)


@app.route('/api/reset', methods=['POST'])
def reset():
    session.clear()
    return jsonify({"currentIndex": 0, "score": 0, "answered": []})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)