const statusEl = document.getElementById("status");
const wordEl = document.getElementById("word");
const debugEl = document.getElementById("debug");

const startBtn = document.getElementById("startBtn");
const seenBtn = document.getElementById("seenBtn");
const newBtn = document.getElementById("newBtn");

startBtn.onclick = () => {
  game.startGame();
  render();
};

seenBtn.onclick = () => {
  game.answerSeen();
  render();
};

newBtn.onclick = () => {
  game.answerNew();
  render();
};

function render() {
  const state = game.getState();

  statusEl.textContent =
    `Score: ${state.currentScore} | Lives: ${state.lives} | ` +
    `Timer: ${state.timerValue}s | State: ${state.gameState}`;

  wordEl.textContent = state.currentWordData.word || "";

  debugEl.textContent = JSON.stringify(state, null, 2);
}

/* Poll render so timer updates show */
setInterval(() => {
  if (game.getState().gameState === "PLAYING") {
    render();
  }
}, 100);
