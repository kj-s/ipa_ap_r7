const questions = window.QUESTIONS || [];
const categoryNames = {
  T: "テクノロジ",
  M: "マネジメント",
  S: "ストラテジ",
  Ｔ: "テクノロジ",
  Ｍ: "マネジメント",
  Ｓ: "ストラテジ",
};

const state = {
  index: Number(localStorage.getItem("ap-current-index") || 0),
  selected: JSON.parse(localStorage.getItem("ap-selected") || "{}"),
  revealed: false,
};

const progressText = document.querySelector("#progressText");
const progressBar = document.querySelector("#progressBar");
const questionNumber = document.querySelector("#questionNumber");
const categoryBadge = document.querySelector("#categoryBadge");
const imageStack = document.querySelector("#imageStack");
const result = document.querySelector("#result");
const toggleAnswer = document.querySelector("#toggleAnswer");
const prevButton = document.querySelector("#prevButton");
const nextButton = document.querySelector("#nextButton");
const jumpSelect = document.querySelector("#jumpSelect");
const choiceButtons = [...document.querySelectorAll(".choice")];

function clampIndex(index) {
  return Math.max(0, Math.min(questions.length - 1, index));
}

function saveState() {
  localStorage.setItem("ap-current-index", String(state.index));
  localStorage.setItem("ap-selected", JSON.stringify(state.selected));
}

function renderJumpSelect() {
  jumpSelect.replaceChildren(
    ...questions.map((question, index) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = `問${question.number}`;
      return option;
    }),
  );
}

function render() {
  state.index = clampIndex(state.index);
  const question = questions[state.index];
  const currentAnswer = state.selected[question.number];
  const percent = ((state.index + 1) / questions.length) * 100;

  progressText.textContent = `問${question.number} / ${questions.length}`;
  progressBar.style.width = `${percent}%`;
  questionNumber.textContent = `問${question.number}`;
  categoryBadge.textContent = categoryNames[question.category] || question.category;
  jumpSelect.value = String(state.index);

  imageStack.replaceChildren(
    ...question.images.map((src) => {
      const img = document.createElement("img");
      img.src = src;
      img.alt = `問${question.number}`;
      img.loading = "eager";
      return img;
    }),
  );

  choiceButtons.forEach((button) => {
    const choice = button.dataset.choice;
    button.classList.toggle("selected", currentAnswer === choice);
    button.classList.toggle("correct", state.revealed && question.answer === choice);
    button.classList.toggle(
      "incorrect",
      state.revealed && currentAnswer === choice && currentAnswer !== question.answer,
    );
  });

  if (state.revealed) {
    const mark = currentAnswer === question.answer ? "正解" : "不正解";
    result.textContent = currentAnswer
      ? `${mark}: 正解は ${question.answer}`
      : `正解は ${question.answer}`;
  } else {
    result.textContent = currentAnswer ? `選択: ${currentAnswer}` : "";
  }

  toggleAnswer.textContent = state.revealed ? "解答を隠す" : "解答を表示";
  prevButton.disabled = state.index === 0;
  nextButton.disabled = state.index === questions.length - 1;
  saveState();
}

function move(delta) {
  state.index = clampIndex(state.index + delta);
  state.revealed = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
  render();
}

choiceButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const question = questions[state.index];
    state.selected[question.number] = button.dataset.choice;
    render();
  });
});

toggleAnswer.addEventListener("click", () => {
  state.revealed = !state.revealed;
  render();
});

prevButton.addEventListener("click", () => move(-1));
nextButton.addEventListener("click", () => move(1));
jumpSelect.addEventListener("change", () => {
  state.index = Number(jumpSelect.value);
  state.revealed = false;
  render();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft") move(-1);
  if (event.key === "ArrowRight") move(1);
  if (["ア", "イ", "ウ", "エ"].includes(event.key)) {
    const question = questions[state.index];
    state.selected[question.number] = event.key;
    render();
  }
});

renderJumpSelect();
render();
