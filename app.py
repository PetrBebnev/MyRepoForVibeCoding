from flask import Flask, render_template, session, jsonify, request

app = Flask(__name__)
# Секретный ключ обязателен для работы session.
# В продакшене храни его в переменной окружения!
app.secret_key = 'dev-secret-change-me'


# Те же вопросы, что и на клиенте — теперь источник истины на сервере
QUESTIONS = [
    {"correct": 0},  # HTML
    {"correct": 2},  # <link>
    {"correct": 2},  # ===
    {"correct": 1},  # flex-контейнер
    {"correct": 0},  # push()
]


def get_state():
    """Возвращает текущее состояние викторины из session (или дефолтное)."""
    return {
        "currentIndex": session.get("currentIndex", 0),
        "score": session.get("score", 0),
        "answered": session.get("answered", []),  # список индексов отвеченных вопросов
    }


def save_state(state):
    """Сохраняет состояние в session."""
    session["currentIndex"] = state["currentIndex"]
    session["score"] = state["score"]
    session["answered"] = state["answered"]


@app.route('/')
def index():
    state = get_state()
    # Передаём стартовое состояние в шаблон
    return render_template('index.html', state=state)


@app.route('/api/answer', methods=['POST'])
def answer():
    """Пользователь выбрал вариант. Проверяем и обновляем session."""
    data = request.get_json()
    index = data.get('questionIndex')
    chosen = data.get('chosenIndex')

    state = get_state()

    # Защита: вопрос уже отвечен — не даём накликать повторно
    if index in state["answered"]:
        return jsonify(state)

    # Проверка ответа
    if QUESTIONS[index]["correct"] == chosen:
        state["score"] += 1

    state["answered"].append(index)
    save_state(state)
    return jsonify(state)


@app.route('/api/next', methods=['POST'])
def next_question():
    """Переход к следующему вопросу."""
    state = get_state()
    state["currentIndex"] += 1
    save_state(state)
    return jsonify(state)


@app.route('/api/reset', methods=['POST'])
def reset():
    """Сброс прогресса."""
    session.clear()
    return jsonify({"currentIndex": 0, "score": 0, "answered": []})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)