const questions = [
    {
        text: "Что означает аббревиатура HTML?",
        options: [
            "Hyper Text Markup Language",
            "Home Tool Markup Language",
            "Hyperlinks Text Mark Language",
            "High Tech Modern Language"
        ],
        correct: 0
    },
    {
        text: "Какой тег используется для подключения CSS?",
        options: ["<script>", "<style>", "<link>", "<css>"],
        correct: 2
    },
    {
        text: "Какой оператор в JS обозначает строгое равенство?",
        options: ["=", "==", "===", "!="],
        correct: 2
    },
    {
        text: "Что делает CSS-свойство display: flex?",
        options: [
            "Скрывает элемент",
            "Включает флекс-контейнер",
            "Делает текст жирным",
            "Добавляет тень"
        ],
        correct: 1
    },
    {
        text: "Какой метод добавляет элемент в конец массива в JS?",
        options: ["push()", "pop()", "shift()", "unshift()"],
        correct: 0
    }
];

// Состояние, полученное с сервера
let currentIndex = 0;
let score = 0;
let answeredQuestions = [];
let answered = false;

const questionText   = document.getElementById('question-text');
const optionsBlock   = document.getElementById('options-block');
const nextBtn        = document.getElementById('next-btn');
const currentQEl     = document.getElementById('current-question');
const totalQEl       = document.getElementById('total-questions');
const quizContainer  = document.getElementById('quiz-container');
const resultsEl      = document.getElementById('results');
const scoreEl        = document.getElementById('score');

totalQEl.textContent = questions.length;

// Применяем состояние с сервера
function applyState(state) {
    currentIndex = state.currentIndex ?? 0;
    score = state.score ?? 0;
    answeredQuestions = state.answered ?? [];
}

// Отрисовать текущий вопрос
function renderQuestion() {
    answered = answeredQuestions.includes(currentIndex);
    nextBtn.disabled = !answered;
    nextBtn.textContent = (currentIndex === questions.length - 1) ? 'Завершить' : 'Далее';

    const q = questions[currentIndex];
    questionText.textContent = q.text;
    currentQEl.textContent = currentIndex + 1;
    optionsBlock.innerHTML = '';

    q.options.forEach((opt, i) => {
        const btn = document.createElement('button');
        btn.className = 'option';
        btn.textContent = opt;
        btn.addEventListener('click', () => selectAnswer(i));

        if (answered) {
            if (i === q.correct) btn.classList.add('correct');
            btn.disabled = true;
        }

        optionsBlock.appendChild(btn);
    });
}

// Выбор ответа — отправляем на сервер
async function selectAnswer(index) {
    if (answered) return;
    answered = true;
    nextBtn.disabled = false;

    const correct = questions[currentIndex].correct;
    const buttons = optionsBlock.querySelectorAll('.option');

    buttons.forEach((btn, i) => {
        if (i === correct) btn.classList.add('correct');
        else if (i === index) btn.classList.add('wrong');
        btn.disabled = true;
    });

    // Сообщаем серверу
    try {
        const res = await fetch('/api/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                questionIndex: currentIndex,
                chosenIndex: index
            })
        });
        const state = await res.json();
        applyState(state);
        scoreEl.textContent = score; // на случай, если уже показываем результат
    } catch (e) {
        console.error('Ошибка сохранения ответа:', e);
    }
}

// Переход к следующему
nextBtn.addEventListener('click', async () => {
    try {
        const res = await fetch('/api/next', { method: 'POST' });
        const state = await res.json();
        applyState(state);
    } catch (e) {
        console.error('Ошибка перехода:', e);
        return;
    }

    if (currentIndex < questions.length) {
        renderQuestion();
    } else {
        showResults();
    }
});

// Результаты
function showResults() {
    quizContainer.style.display = 'none';
    resultsEl.style.display = 'block';
    scoreEl.textContent = score;
}

// Кнопка «Пройти снова» — сбрасываем session на сервере
document.addEventListener('DOMContentLoaded', () => {
    const restartBtn = document.getElementById('restart-btn');
    if (restartBtn) {
        restartBtn.addEventListener('click', async () => {
            await fetch('/api/reset', { method: 'POST' });
            location.reload();
        });
    }
});

// Старт
(function init() {
    applyState(window.INITIAL_STATE || {});
    if (currentIndex >= questions.length) {
        showResults();
    } else {
        renderQuestion();
    }
})();