# tests/test_quiz.py
import pytest
from importlib import import_module

app_module = import_module("app")
app = app_module.app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    with app.test_client() as c:
        yield c


@pytest.fixture
def questions():
    return app_module.QUESTIONS


# ============================================================
# Обычный сценарий (happy path)
# ============================================================

def test_index_returns_200_and_initial_state(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "INITIAL_STATE" in body
    assert '"currentIndex": 0' in body or '"currentIndex":0' in body
    assert '"score": 0' in body or '"score":0' in body


def test_correct_answer_increments_score(client, questions):
    resp = client.post("/api/answer", json={"chosenIndex": questions[0]["correct"]})
    assert resp.status_code == 200
    state = resp.get_json()
    assert state["score"] == 1
    assert state["answered"] == [0]


def test_wrong_answer_does_not_increment_score(client, questions):
    wrong = (questions[0]["correct"] + 1) % 4
    resp = client.post("/api/answer", json={"chosenIndex": wrong})
    assert resp.status_code == 200
    state = resp.get_json()
    assert state["score"] == 0
    assert state["answered"] == [0]


def test_next_increments_current_index(client, questions):
    client.post("/api/answer", json={"chosenIndex": questions[0]["correct"]})
    resp = client.post("/api/next")
    assert resp.status_code == 200
    assert resp.get_json()["currentIndex"] == 1


def test_full_quiz_pass(client, questions):
    for q in questions:
        r = client.post("/api/answer", json={"chosenIndex": q["correct"]})
        assert r.status_code == 200
        r = client.post("/api/next")
        assert r.status_code == 200
    state = r.get_json()
    assert state["score"] == len(questions)
    assert state["currentIndex"] == len(questions)


def test_reset_clears_session(client, questions):
    client.post("/api/answer", json={"chosenIndex": questions[0]["correct"]})
    client.post("/api/next")
    resp = client.post("/api/reset")
    assert resp.status_code == 200
    assert resp.get_json() == {"currentIndex": 0, "score": 0, "answered": []}

    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert '"score": 0' in body or '"score":0' in body


def test_state_persists_between_requests(client, questions):
    client.post("/api/answer", json={"chosenIndex": questions[0]["correct"]})
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert '"score": 1' in body or '"score":1' in body


def test_score_summary_after_mixed_answers(client, questions):
    answers = [
        questions[0]["correct"],
        (questions[1]["correct"] + 1) % 4,  # wrong
        questions[2]["correct"],
        (questions[3]["correct"] + 1) % 4,  # wrong
        questions[4]["correct"],
    ]
    state = None
    for a in answers:
        r = client.post("/api/answer", json={"chosenIndex": a})
        state = r.get_json()
        client.post("/api/next")
    assert state["score"] == 3


# ============================================================
# Ошибочный сценарий (error / negative path)
# ============================================================

def test_repeat_answer_is_idempotent(client, questions):
    client.post("/api/answer", json={"chosenIndex": questions[0]["correct"]})
    resp = client.post("/api/answer", json={"chosenIndex": questions[0]["correct"]})
    assert resp.status_code == 200
    assert resp.get_json()["score"] == 1


def test_answer_with_out_of_range_chosen_index(client):
    resp = client.post("/api/answer", json={"chosenIndex": 99})
    assert resp.status_code == 400


def test_answer_with_negative_chosen_index(client):
    resp = client.post("/api/answer", json={"chosenIndex": -1})
    assert resp.status_code == 400


def test_answer_without_json_body(client):
    resp = client.post("/api/answer", data="not-json", content_type="text/plain")
    assert resp.status_code == 400


def test_answer_with_non_numeric_chosen_index(client):
    resp = client.post("/api/answer", json={"chosenIndex": "abc"})
    assert resp.status_code == 400


def test_answer_with_bool_chosen_index(client):
    # True/False — это подкласс int, но не должен приниматься как индекс
    resp = client.post("/api/answer", json={"chosenIndex": True})
    assert resp.status_code == 400


def test_answer_after_quiz_finished(client, questions):
    # Проходим всю викторину
    for q in questions:
        client.post("/api/answer", json={"chosenIndex": q["correct"]})
        client.post("/api/next")
    # Теперь currentIndex == len(questions); ещё один ответ — 400
    resp = client.post("/api/answer", json={"chosenIndex": 0})
    assert resp.status_code == 400


def test_next_without_answering(client):
    resp = client.post("/api/next")
    assert resp.status_code == 200
    # Индекс растёт, но вопрос не отвечен
    assert resp.get_json()["currentIndex"] == 1
    assert resp.get_json()["answered"] == []


def test_many_next_calls_do_not_overshoot(client, questions):
    for _ in range(len(questions) + 5):
        resp = client.post("/api/next")
    state = resp.get_json()
    # currentIndex не должен уйти за пределы списка
    assert state["currentIndex"] == len(questions)


def test_reset_on_clean_client(client):
    resp = client.post("/api/reset")
    assert resp.status_code == 200
    assert resp.get_json() == {"currentIndex": 0, "score": 0, "answered": []}


def test_answer_ignores_client_question_index(client, questions):
    """Если клиент пришлёт questionIndex — сервер должен его игнорировать."""
    # Переходим на 2-й вопрос (индекс 1)
    client.post("/api/next")
    # Шлём подложный questionIndex: 0, но отвечаем на вопрос по currentIndex (1)
    resp = client.post("/api/answer", json={"questionIndex": 0, "chosenIndex": questions[1]["correct"]})
    assert resp.status_code == 200
    state = resp.get_json()
    # Ответ засчитан на текущий вопрос (индекс 1), а не на 0
    assert 1 in state["answered"]
    assert state["score"] == 1


# ============================================================
# Крайние случаи (edge cases)
# ============================================================

def test_answer_last_question(client, questions):
    # Прогоняем до последнего вопроса
    for _ in range(len(questions) - 1):
        client.post("/api/next")
    idx = len(questions) - 1
    resp = client.post("/api/answer", json={"chosenIndex": questions[idx]["correct"]})
    assert resp.status_code == 200
    resp = client.post("/api/next")
    assert resp.get_json()["currentIndex"] == len(questions)


def test_all_answers_correct(client, questions):
    for q in questions:
        client.post("/api/answer", json={"chosenIndex": q["correct"]})
        client.post("/api/next")
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert f'"score": {len(questions)}' in body or f'"score":{len(questions)}' in body


def test_all_answers_wrong(client, questions):
    for q in questions:
        wrong = (q["correct"] + 1) % 4
        client.post("/api/answer", json={"chosenIndex": wrong})
        client.post("/api/next")
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert '"score": 0' in body or '"score":0' in body


def test_chosen_index_at_boundaries(client, questions):
    # Валидные границы: 0 и 3 — должны приниматься
    r = client.post("/api/answer", json={"chosenIndex": 0})
    assert r.status_code == 200
    client.post("/api/reset")
    client.post("/api/next")
    r = client.post("/api/answer", json={"chosenIndex": 3})
    assert r.status_code == 200


def test_first_request_empty_session(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_reload_after_completion(client, questions):
    for q in questions:
        client.post("/api/answer", json={"chosenIndex": q["correct"]})
        client.post("/api/next")
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert f'"currentIndex": {len(questions)}' in body or f'"currentIndex":{len(questions)}' in body


def test_two_clients_independent(client, questions):
    client_a = app.test_client()
    client_b = app.test_client()
    client_a.post("/api/answer", json={"chosenIndex": questions[0]["correct"]})
    r = client_b.get("/")
    body = r.get_data(as_text=True)
    assert '"score": 0' in body or '"score":0' in body


def test_reset_during_progress(client, questions):
    for i in range(3):
        client.post("/api/answer", json={"chosenIndex": questions[i]["correct"]})
        client.post("/api/next")
    client.post("/api/reset")
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert '"currentIndex": 0' in body or '"currentIndex":0' in body
    assert '"score": 0' in body or '"score":0' in body


def test_empty_questions_list(monkeypatch):
    mod = import_module("app")
    monkeypatch.setattr(mod, "QUESTIONS", [])
    with mod.app.test_client() as c:
        resp = c.get("/")
        assert resp.status_code == 200


def test_non_json_body(client):
    """Пустое тело — request.get_json(silent=True) вернёт None, ответ 400."""
    resp = client.post("/api/answer")
    assert resp.status_code == 400